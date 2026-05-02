"""
tpm_core.orchestrator - LangGraph minimal flow (Phase 2 demo)
ref: MASTER_PLAN_v5.md § 10.4

Minimal pipeline (Phase 2 scope):
    INIT -> CLARIFY (loop) -> PLAN (search L3) -> DONE

Future phases will add: WORK (worker subgraphs), AUDIT, HUMAN_GATE.
"""
from __future__ import annotations

import logging
import os
from typing import Callable, Optional

from langgraph.graph import END, StateGraph

from tpm_core.clarification import (
    generate_clarification_question,
    parse_intent,
    to_intent,
    user_wants_to_skip,
)
from tpm_core.llm import chat
from tpm_core.state import (
    HandoffPacket,
    Intent,
    OrchestratorPhase,
    TPMState,
)

log = logging.getLogger(__name__)

DEFAULT_MODEL = os.getenv("TPM_ORCHESTRATOR_MODEL", "qwen3:8b")


# ============================================================
# UI callback - injected by caller (CLI or Chainlit later)
# ============================================================
class UI:
    """Minimal UI contract. CLI demo + Chainlit both implement this."""
    def ask(self, question: str, options: list[str]) -> str:
        raise NotImplementedError

    def info(self, msg: str) -> None:
        print(msg)


class StdinUI(UI):
    def ask(self, question: str, options: list[str]) -> str:
        print()
        print(f"AI: {question}")
        for opt in options:
            print(f"  {opt}")
        try:
            ans = input("You: ").strip()
        except EOFError:
            ans = ""
        return ans


# ============================================================
# Nodes
# ============================================================
def node_init(state: TPMState) -> TPMState:
    log.info("[init] session=%s request=%r", state.session_id, state.user_request[:80])
    state.phase = OrchestratorPhase.CLARIFY
    state.clarify_history = [state.user_request]
    state.append_handoff(HandoffPacket(
        stage="init",
        reasoning=f"new session {state.session_id}",
        payload={"request_chars": len(state.user_request)},
    ))
    return state


def make_clarify_node(ui: UI, model: str) -> Callable[[TPMState], TPMState]:
    """Returns a node closure that uses the given UI for asking questions."""

    def node_clarify(state: TPMState) -> TPMState:
        # Skip clarification if user explicitly said so or already iterated max
        latest = state.clarify_history[-1] if state.clarify_history else ""
        if user_wants_to_skip(latest):
            ui.info("[clarify] user requested skip - using best guess + flag")
            intent_dict = parse_intent(model, state.clarify_history)
            intent = to_intent(intent_dict, state.clarify_history)
            intent.user_override = True
            state.intent = intent
            state.phase = OrchestratorPhase.PLAN
            state.append_handoff(HandoffPacket(
                stage="clarify",
                success=True,
                confidence=intent.confidence,
                reasoning="user_skip - proceed with best guess",
                payload={"intent": intent.model_dump()},
            ))
            return state

        # Parse intent
        intent_dict = parse_intent(model, state.clarify_history)
        confidence = float(intent_dict.get("confidence", 0.0))
        log.info(
            "[clarify] iter=%d confidence=%.2f action=%r subject=%r",
            state.clarify_iterations,
            confidence,
            intent_dict.get("action"),
            intent_dict.get("subject"),
        )

        # Confidence high enough -> ask user to confirm once, then proceed
        if confidence >= state.clarify_min_confidence:
            intent = to_intent(intent_dict, state.clarify_history)
            ui.info("\nAI proposes:")
            ui.info(f"  Action:  {intent.action}")
            ui.info(f"  Subject: {intent.subject}")
            ui.info(f"  Scope:   {intent.scope}")
            ans = ui.ask(
                "Confirm to proceed? (yes/แก้ไข)",
                options=["yes - go ahead", "แก้ไข - revise"],
            )
            if ans.strip().lower() in ("yes", "y", "ใช่", "go", ""):
                state.intent = intent
                state.phase = OrchestratorPhase.PLAN
                state.append_handoff(HandoffPacket(
                    stage="clarify",
                    success=True,
                    confidence=confidence,
                    reasoning="user confirmed final intent",
                    payload={"intent": intent.model_dump()},
                ))
                return state
            # User wants to revise -> add to history + loop
            state.clarify_history.append(ans)
            state.clarify_iterations += 1
            return _check_max_iter(state)

        # Confidence too low -> ask clarification question
        try:
            q = generate_clarification_question(model, state.clarify_history, intent_dict)
        except Exception as e:  # noqa: BLE001
            log.error("[clarify] question gen failed: %s", e)
            q = {
                "question": "ผมยังไม่แน่ใจคำขอของคุณ ขอรายละเอียดเพิ่มได้ไหมครับ?",
                "options": ["พิมพ์อธิบายเพิ่ม"],
            }
        question = q.get("question", "")
        options = q.get("options", []) or []
        state.pending_question = question
        state.pending_options = options
        ans = ui.ask(question, options)
        state.clarify_history.append(ans)
        state.clarify_iterations += 1
        return _check_max_iter(state)

    return node_clarify


def _check_max_iter(state: TPMState) -> TPMState:
    if state.clarify_iterations >= state.clarify_max_iterations:
        log.warning("[clarify] hit max iterations - proceeding with low-confidence intent")
        # Build best-effort intent and proceed
        state.phase = OrchestratorPhase.PLAN
        if state.intent is None:
            state.intent = Intent(
                action="other",
                subject="",
                scope=state.clarify_history[-1] if state.clarify_history else "",
                confidence=0.4,
                user_override=True,
                history=state.clarify_history,
            )
    return state


def make_plan_node(ui: UI, model: str) -> Callable[[TPMState], TPMState]:
    """Phase-2-minimal: classify intent into search lane + run L3."""
    from tpm_search import Intent as SearchIntent
    from tpm_search import search as l3_search
    from tpm_search.egress import EgressBlocked

    def node_plan(state: TPMState) -> TPMState:
        intent = state.intent
        if intent is None:
            state.phase = OrchestratorPhase.FAILED
            state.error = "plan: no confirmed intent"
            return state

        # Map clarification intent to search intent (lane signals)
        s_intent = SearchIntent(
            is_definition=intent.is_definition,
            is_standard_reference=intent.is_standard_reference,
            needs_grounding=intent.needs_grounding,
            has_output_schema=intent.has_output_schema,
            output_schema=intent.output_schema,
            feed_to_llm=intent.feed_to_llm,
            is_recent=intent.is_recent,
            is_research=intent.is_research,
            is_simple_lookup=intent.is_simple_lookup,
        )

        # Build search query from intent slots (combine for better recall)
        parts: list[str] = []
        if intent.subject:
            parts.append(intent.subject)
        if intent.scope and intent.scope.strip().lower() not in (
            intent.subject.strip().lower(),
            "definition",
            "info",
            "details",
        ):
            parts.append(intent.scope)
        query = " ".join(parts) if parts else state.user_request

        ui.info(f"\n[plan] L3 query: {query!r}")
        try:
            results = l3_search(query, intent=s_intent)
        except EgressBlocked as e:
            state.phase = OrchestratorPhase.FAILED
            state.error = f"egress blocked: {e}"
            ui.info(f"[FAIL] {state.error}")
            return state

        state.recon_results = {
            "provider": results.provider.value,
            "n_results": len(results.results),
            "fallback_chain": [p.value for p in results.fallback_chain],
            "first": (
                results.results[0].model_dump() if results.results else None
            ),
            "all_titles": [r.title for r in results.results[:5]],
        }
        state.recon_quality = 1.0 if results.is_useful() else 0.0
        state.recon_complete = True

        ui.info(
            f"[plan] {results.provider.value} returned "
            f"{len(results.results)} results "
            f"(latency={results.latency_ms}ms, "
            f"quota={results.quota_remaining})"
        )
        for r in results.results[:3]:
            ui.info(f"  - {r.title[:80]}")
            if r.snippet:
                ui.info(f"      {r.snippet[:120]}")

        # Phase 2 minimal: end here
        state.phase = OrchestratorPhase.DONE
        state.final_output = {
            "intent": intent.model_dump(),
            "search": state.recon_results,
        }
        state.append_handoff(HandoffPacket(
            stage="plan",
            success=True,
            reasoning=f"L3 search via {results.provider.value}",
            payload={"n_results": len(results.results)},
        ))
        return state

    return node_plan


# ============================================================
# Build graph
# ============================================================
def build_graph(ui: UI | None = None, model: str = DEFAULT_MODEL):
    ui = ui or StdinUI()
    g = StateGraph(TPMState)
    g.add_node("init", node_init)
    g.add_node("clarify", make_clarify_node(ui, model))
    g.add_node("plan", make_plan_node(ui, model))

    g.set_entry_point("init")
    g.add_edge("init", "clarify")

    def clarify_router(state: TPMState) -> str:
        if state.phase == OrchestratorPhase.PLAN:
            return "plan"
        if state.phase == OrchestratorPhase.FAILED:
            return END
        # Still clarifying
        return "clarify"

    g.add_conditional_edges(
        "clarify",
        clarify_router,
        {"clarify": "clarify", "plan": "plan", END: END},
    )
    g.add_edge("plan", END)
    return g.compile()


# ============================================================
# Convenience runner
# ============================================================
def run_orchestrator(
    user_request: str,
    ui: UI | None = None,
    model: str = DEFAULT_MODEL,
) -> TPMState:
    graph = build_graph(ui=ui, model=model)
    initial = TPMState(user_request=user_request, model_name=model)
    final = graph.invoke(initial)
    # LangGraph returns dict-like - convert back
    if isinstance(final, dict):
        return TPMState(**final)
    return final
