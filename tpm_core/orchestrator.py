"""
tpm_core.orchestrator - LangGraph minimal flow (Phase 2)
ref: MASTER_PLAN_v6.md § 10.4

Pipeline (Phase 2 scope):
    INIT -> CLARIFY (loop) -> INQUIRY (Section 8) -> PLAN (search L3 / worker) -> DONE

INQUIRY is a no-LLM node: deterministic skip rules (general knowledge,
night cycle, emergency) + pattern-based user-specific detection.

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
from tpm_core.inquiry import (
    build_inquiry_prompt,
    parse_inquiry_answer,
    should_inquire,
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
            state.phase = OrchestratorPhase.INQUIRY
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
            if _is_yes(ans):
                state.intent = intent
                state.phase = OrchestratorPhase.INQUIRY
                state.append_handoff(HandoffPacket(
                    stage="clarify",
                    success=True,
                    confidence=confidence,
                    reasoning="user confirmed final intent",
                    payload={"intent": intent.model_dump()},
                ))
                return state
            # User wants to revise -> get the ACTUAL revision content,
            # not the button label "แก้ไข - revise"
            revision = ans.strip()
            if _is_revise_label(revision):
                revision = ui.ask(
                    "ช่วยอธิบายเพิ่มเติม — คุณอยากให้ปรับอะไร? "
                    "(เช่น เปลี่ยน subject, เพิ่มเงื่อนไขเวลา, ภาษาตอบกลับ ฯลฯ)",
                    options=[],
                ).strip()
            if revision:
                state.clarify_history.append(revision)
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


# ============================================================
# Answer interpretation helpers
# ============================================================
_YES_TOKENS = {"yes", "y", "ใช่", "go", "ตกลง", "ok", "ยืนยัน", "ครับ", "ค่ะ", ""}
_REVISE_LABELS = {
    "แก้ไข - revise",
    "แก้ไข",
    "revise",
    "no",
    "ไม่ใช่",
    "ไม่",
    "ไม่ตรง",
}


def _is_yes(answer: str) -> bool:
    """User clicked 'yes' or typed a confirmation token."""
    return answer.strip().lower() in _YES_TOKENS


def _is_revise_label(answer: str) -> bool:
    """User clicked 'แก้ไข' button - the literal label, not real content."""
    return answer.strip().lower() in {s.lower() for s in _REVISE_LABELS}


def _check_max_iter(state: TPMState) -> TPMState:
    if state.clarify_iterations >= state.clarify_max_iterations:
        log.warning("[clarify] hit max iterations - proceeding with low-confidence intent")
        # Build best-effort intent and proceed
        state.phase = OrchestratorPhase.INQUIRY
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


def make_inquiry_node(ui: UI) -> Callable[[TPMState], TPMState]:
    """
    Inquiry-First node (Section 8). Runs after clarify, before plan.
    Asks the user for user-specific info before sending the query to L3 search.
    No LLM call - decision is deterministic (pattern + intent slot based).
    """

    def node_inquiry(state: TPMState) -> TPMState:
        intent = state.intent
        if intent is None:
            # Should never happen - clarify guarantees intent before INQUIRY
            state.phase = OrchestratorPhase.PLAN
            state.inquiry_route = "skipped"
            state.inquiry_skip_reason = "no_intent"
            return state

        decision = should_inquire(intent, state.user_request)

        if decision.skip:
            state.inquiry_route = "skipped"
            state.inquiry_skip_reason = decision.reason
            state.phase = OrchestratorPhase.PLAN
            state.append_handoff(HandoffPacket(
                stage="inquiry",
                success=True,
                reasoning=f"skipped: {decision.reason}",
                payload={"route": "skipped", "reason": decision.reason},
            ))
            log.info("[inquiry] skipped (%s)", decision.reason)
            return state

        # Ask the user
        prompt = build_inquiry_prompt(intent, decision)
        state.inquiry_question = prompt["question"]
        ans_text = ui.ask(prompt["question"], prompt["options"])
        state.inquiry_answer = ans_text

        parsed = parse_inquiry_answer(ans_text)
        state.inquiry_route = parsed.route
        state.inquiry_payload = parsed.payload

        # If user provided a direct answer, fold it into intent.scope so the
        # downstream synthesizer has it. If they pointed at a location, the
        # plan node will pick it up via state.inquiry_payload.
        if parsed.route == "user_answered" and parsed.payload:
            # Append as an extra scope hint without clobbering the original
            extra = parsed.payload
            if intent.scope and extra not in intent.scope:
                intent.scope = f"{intent.scope} | user-provided: {extra}"
            elif not intent.scope:
                intent.scope = f"user-provided: {extra}"
            state.intent = intent

        state.phase = OrchestratorPhase.PLAN
        state.append_handoff(HandoffPacket(
            stage="inquiry",
            success=True,
            reasoning=f"asked user; route={parsed.route}",
            payload={
                "route": parsed.route,
                "target": decision.target_phrase,
                "answer_chars": len(parsed.payload),
            },
        ))
        log.info(
            "[inquiry] asked about %r -> route=%s payload_chars=%d",
            decision.target_phrase, parsed.route, len(parsed.payload),
        )
        return state

    return node_inquiry


SYNTHESIZER_SYSTEM = """\
You are a TPM (Total Productive Maintenance) engineering assistant.
Given a user question and search result snippets, write a concise, accurate answer.

Rules:
  - Cite sources inline as [1], [2], [3] matching the snippet numbers.
  - If the snippets do not contain enough info to answer, say so honestly.
  - Do NOT invent numbers, dates, or facts that aren't in the snippets.
  - Keep the answer under 6 sentences unless the user asked for detail.
  - Match the user's preferred language (see "Reply language" field below).
  - End with a "**Sources:**" list of the cited URLs.
"""


def make_plan_node(ui: UI, model: str) -> Callable[[TPMState], TPMState]:
    """
    Phase 2/3: route intent to either L3 search (lookup) or Worker (report/excel/calc).
    """
    from tpm_search import Intent as SearchIntent
    from tpm_search import search as l3_search
    from tpm_search.egress import EgressBlocked, classify
    from tpm_search.types import Classification

    # Worker actions vs lookup actions
    WORKER_ACTIONS = {"report", "excel", "calc", "edit", "analyze"}

    def node_plan(state: TPMState) -> TPMState:
        intent = state.intent
        if intent is None:
            state.phase = OrchestratorPhase.FAILED
            state.error = "plan: no confirmed intent"
            return state

        # Bug #4 fix: data-classification gate at the PLAN node, before any
        # routing. Catches CONFIDENTIAL/RESTRICTED subjects that previously
        # slipped past the L3-only egress check when the intent action was
        # report/analyze/excel (which dispatches to a local worker without
        # touching L3). The L3 egress check still runs further down as
        # defense in depth.
        cls = classify(f"{intent.subject} {state.user_request}")
        if cls in (Classification.CONFIDENTIAL, Classification.RESTRICTED):
            state.phase = OrchestratorPhase.FAILED
            state.error = (
                f"egress blocked: classification={cls.value} for subject "
                f"{intent.subject!r} - data-classification gate at plan node"
            )
            ui.info(f"[FAIL] {state.error}")
            return state

        # ----- Route 1: Worker (report / excel / calc) -----
        if intent.action.lower() in WORKER_ACTIONS:
            return _run_worker_branch(state, intent, ui)

        # ----- Route 2: L3 search (lookup) -----
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

        # Synthesize an actual answer from the snippets (not just a title list).
        synthesis = ""
        if results.is_useful() and results.results:
            try:
                synthesis = _synthesize_lookup_answer(
                    user_request=state.user_request,
                    intent=intent,
                    results=results,
                    model=model,
                )
                ui.info("\n💡 **คำตอบ:**\n\n" + synthesis)
            except Exception as e:  # noqa: BLE001
                log.warning("synthesis failed: %s", e)
                # Fall back to title list
                for r in results.results[:3]:
                    ui.info(f"  - {r.title[:80]}")
                    if r.snippet:
                        ui.info(f"      {r.snippet[:120]}")

        state.phase = OrchestratorPhase.DONE
        state.final_output = {
            "intent": intent.model_dump(),
            "search": state.recon_results,
            "answer": synthesis,
        }
        state.append_handoff(HandoffPacket(
            stage="plan",
            success=True,
            reasoning=f"L3 search via {results.provider.value} + synthesis",
            payload={"n_results": len(results.results), "answer_chars": len(synthesis)},
        ))
        return state

    return node_plan


def _synthesize_lookup_answer(
    user_request: str,
    intent: Intent,
    results,
    model: str,
) -> str:
    """
    Use the LLM to read the top search snippets and write an answer in the
    user's preferred language. Cites sources inline.

    Snippet budget tuned for 8K context (tpm-orch:latest):
      8 snippets x 800 chars = ~6400 chars (~1600 tokens)
      + system prompt + user q + answer (~1500 tokens)
      = ~3-4K tokens, well within 8K ctx, leaves room for chat history.
    """
    from tpm_core.llm import chat

    # Decide budget based on whether we're on tpm-orch (8K) or default (4K)
    is_custom_model = model.startswith("tpm-")
    n_snippets = 8 if is_custom_model else 5
    chunk_chars = 800 if is_custom_model else 400

    snippets = []
    for i, r in enumerate(results.results[:n_snippets], 1):
        chunk = (r.snippet or r.title or "").strip()
        snippets.append(
            f"[{i}] {r.title}\n  URL: {r.url}\n  Content: {chunk[:chunk_chars]}"
        )

    # Detect target language from intent.constraints, else from prompt heuristic
    lang = (intent.constraints or {}).get("language", "")
    if not lang:
        # Heuristic: if user prompt has Thai chars, reply Thai; else English
        if any("฀" <= c <= "๿" for c in user_request):
            lang = "th"
        else:
            lang = "en"
    lang_label = {"th": "Thai (ภาษาไทย)", "en": "English"}.get(lang, lang)

    user_msg = (
        f"User question: {user_request}\n\n"
        f"Reply language: {lang_label}\n\n"
        f"Search snippets:\n" + "\n\n".join(snippets) +
        "\n\nWrite the answer now. Remember to cite [1] [2] [3] inline."
    )

    return chat(
        model,
        [
            {"role": "system", "content": SYNTHESIZER_SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.2,
        timeout=180.0,
    )


# ============================================================
# Worker dispatch (Phase 3)
# ============================================================
def _run_worker_branch(state: TPMState, intent: Intent, ui: UI) -> TPMState:
    """
    Route intent.action to the appropriate worker.
    """
    from pathlib import Path

    from tpm_workers.base import WorkerInput, WorkerType
    from tpm_workers.data_loader import list_equipment_tags
    from tpm_workers.excel import run_excel_worker
    from tpm_workers.report import run_report_worker

    # Resolve target equipment from intent.subject - try fuzzy match
    target = intent.subject or ""
    if target:
        known = list_equipment_tags()
        # exact tag match wins
        if target not in known:
            # case-insensitive substring match
            matches = [t for t in known if target.lower() in t.lower()]
            if len(matches) == 1:
                target = matches[0]
                ui.info(f"[plan] resolved subject {intent.subject!r} -> {target!r}")
            elif len(matches) > 1:
                ui.info(f"[plan] ambiguous subject {intent.subject!r} matches: {matches}")
                state.phase = OrchestratorPhase.FAILED
                state.error = f"ambiguous equipment tag: {matches}"
                return state

    worker_type = (
        WorkerType.EXCEL if intent.action.lower() in ("excel", "calc") else WorkerType.REPORT
    )
    output_subdir = (
        "reports" if worker_type == WorkerType.REPORT
        else "excel"
    )
    inp = WorkerInput(
        worker_type=worker_type,
        session_id=state.session_id,
        user_request=state.user_request,
        intent=intent.model_dump(),
        target_subject=target or "",
        time_range_days=int(intent.constraints.get("time_range_days", 90)),
        output_dir=Path("output") / output_subdir,
    )

    ui.info(f"\n[plan] dispatch worker: {inp.worker_type.value} for {inp.target_subject!r}")

    if inp.worker_type == WorkerType.REPORT:
        result = run_report_worker(inp, model=DEFAULT_MODEL)
    else:
        result = run_excel_worker(inp)

    # Pretty-print summary
    ui.info("")
    ui.info(f"[{inp.worker_type.value} worker] {result.summary}")
    for s in result.steps:
        notes = "; ".join(s.notes) if s.notes else "-"
        ui.info(f"  [{s.name:10s}] success={s.success}  {notes}")
    if result.auditor_findings:
        ui.info(f"  Auditor findings: {result.auditor_findings}")
    for f in result.output_files:
        ui.info(f"  -> {f}")

    state.subtask_results[inp.worker_type.value] = result.model_dump(mode="json")
    state.phase = OrchestratorPhase.DONE if result.success else OrchestratorPhase.FAILED
    state.final_output = {
        "intent": intent.model_dump(),
        "worker": inp.worker_type.value,
        "output_files": result.output_files,
        "metrics": result.metrics,
        "summary": result.summary,
        "auditor_passed": result.auditor_passed,
        "auditor_findings": result.auditor_findings,
    }
    state.append_handoff(HandoffPacket(
        stage=f"worker_{inp.worker_type.value}",
        success=result.success,
        confidence=result.confidence,
        reasoning=result.summary,
        payload={"n_files": len(result.output_files)},
    ))
    return state




# ============================================================
# Build graph
# ============================================================
def build_graph(ui: UI | None = None, model: str = DEFAULT_MODEL):
    ui = ui or StdinUI()
    g = StateGraph(TPMState)
    g.add_node("init", node_init)
    g.add_node("clarify", make_clarify_node(ui, model))
    g.add_node("inquiry", make_inquiry_node(ui))
    g.add_node("plan", make_plan_node(ui, model))

    g.set_entry_point("init")
    g.add_edge("init", "clarify")

    def clarify_router(state: TPMState) -> str:
        if state.phase == OrchestratorPhase.INQUIRY:
            return "inquiry"
        if state.phase == OrchestratorPhase.PLAN:
            return "plan"
        if state.phase == OrchestratorPhase.FAILED:
            return END
        # Still clarifying
        return "clarify"

    def inquiry_router(state: TPMState) -> str:
        if state.phase == OrchestratorPhase.PLAN:
            return "plan"
        if state.phase == OrchestratorPhase.FAILED:
            return END
        return END  # safety fallback

    g.add_conditional_edges(
        "clarify",
        clarify_router,
        {"clarify": "clarify", "inquiry": "inquiry", "plan": "plan", END: END},
    )
    g.add_conditional_edges(
        "inquiry",
        inquiry_router,
        {"plan": "plan", END: END},
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
    persist: bool = True,
) -> TPMState:
    graph = build_graph(ui=ui, model=model)
    initial = TPMState(user_request=user_request, model_name=model)
    started_at = initial.started_at
    final = graph.invoke(initial)
    # LangGraph returns dict-like - convert back
    if isinstance(final, dict):
        final = TPMState(**final)

    # Auto-persist on terminal state (used by Night Cycle replay)
    if persist and final.is_terminal():
        try:
            from tpm_night.session_store import save_session
            save_session(final, started_at=started_at)
        except Exception as e:  # noqa: BLE001
            log.warning("session persistence failed: %s", e)

    return final
