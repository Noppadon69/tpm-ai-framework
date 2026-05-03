"""
app.py - Chainlit web UI entry point for TPM AI
ref: MASTER_PLAN_v5.md § 7.6, § 11, § 22.6

Run:
    chainlit run app.py --host 0.0.0.0 --port 8000
or via launcher:
    bash start.sh   |   start.bat

Open http://localhost:8000 in browser.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

# UTF-8 stdout (Windows console)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

# Load .env if present
_env_file = REPO / ".env"
if _env_file.exists():
    for line in _env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

import chainlit as cl  # noqa: E402

from tpm_core.llm import health  # noqa: E402
from tpm_core.orchestrator import (  # noqa: E402
    DEFAULT_MODEL,
    build_graph,
)
from tpm_core.state import OrchestratorPhase, TPMState  # noqa: E402
from tpm_search.quota import status as quota_status  # noqa: E402
from tpm_ui.bridge import CLARIFY_ACTION_NAME, ChainlitUI, fmt_handoff  # noqa: E402

# Import workers so they're registered (orchestrator may dispatch)
import tpm_workers  # noqa: F401, E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
for noisy in ("httpx", "httpcore", "urllib3", "chainlit", "engineio", "socketio"):
    logging.getLogger(noisy).setLevel(logging.WARNING)


# ============================================================
# Chat lifecycle
# ============================================================
@cl.on_chat_start
async def on_chat_start():
    if not health():
        await cl.Message(
            content="⚠️ **Ollama not reachable**. Start it with `ollama serve`.",
            author="System",
        ).send()
        return

    # Status panel
    quota = quota_status()
    panel_lines = [
        "## 🤖 TPM AI Assistant",
        "",
        f"**Model:** `{DEFAULT_MODEL}`",
        "",
        "**Free-tier quota:**",
        f"- SearXNG (workhorse): unlimited ✅",
        f"- Tavily: {quota.get('tavily',{}).get('remaining','?')}/1000",
        f"- Exa: {quota.get('exa',{}).get('remaining','?')}/1000",
        "",
        "**Try these prompts:**",
        "- `เขียน maintenance report ของ SHIBAURA-EC100SX`",
        "- `report on MAKINO-a51nx last 90 days`",
        "- `excel reliability metrics for SODICK-AD35L`",
        "- `what is ASTM A106 standard`",
        "- `ราคา bearing SKF 6205 ล่าสุด`",
        "",
        "💡 ระบบจะถาม clarification ก่อนเริ่มงาน — กดปุ่มหรือพิมพ์อธิบายเพิ่ม",
    ]
    await cl.Message(content="\n".join(panel_lines), author="System").send()


# ============================================================
# Action button handler (for clarification choices)
# ============================================================
@cl.action_callback(CLARIFY_ACTION_NAME)
async def on_clarify_action(action: cl.Action):
    """Route button click into the ChainlitUI ask queue."""
    queue = cl.user_session.get("ask_queue")
    if queue is None:
        # Spurious click after timeout - just acknowledge
        await cl.Message(
            content="(button click came after the question expired)",
            author="System",
        ).send()
        return
    payload = getattr(action, "payload", None) or {}
    value = payload.get("value") or getattr(action, "value", "") or ""
    await queue.put(str(value))


# ============================================================
# Main message handler
# ============================================================
@cl.on_message
async def on_message(message: cl.Message):
    user_text = message.content.strip()
    if not user_text:
        return

    if user_text.lower() in ("clear", "reset", "/clear", "/reset"):
        cl.user_session.clear()
        await cl.Message(content="🔄 session cleared", author="System").send()
        return

    # If we're currently awaiting an answer (orchestrator paused at ui.ask),
    # route this message to the queue instead of starting a new orchestrator.
    if cl.user_session.get("awaiting_answer"):
        queue = cl.user_session.get("ask_queue")
        if queue is not None:
            await queue.put(user_text)
            return

    # Build orchestrator with this session's UI
    ui = ChainlitUI(ask_timeout_s=600.0)
    graph = build_graph(ui=ui, model=DEFAULT_MODEL)

    initial_state = TPMState(user_request=user_text, model_name=DEFAULT_MODEL)

    # Run orchestrator in worker thread (LangGraph is sync; ui.ask() blocks)
    async with cl.Step(name="Orchestrator", type="run") as root_step:
        root_step.input = user_text

        try:
            started_at = initial_state.started_at
            final = await asyncio.to_thread(graph.invoke, initial_state)
            if isinstance(final, dict):
                final = TPMState(**final)
            # Persist for Night Cycle replay
            if final.is_terminal():
                try:
                    from tpm_night import save_session
                    save_session(final, started_at=started_at)
                except Exception as e:  # noqa: BLE001
                    logging.warning("session persistence failed: %s", e)
        except Exception as e:  # noqa: BLE001
            await cl.Message(
                content=f"❌ Orchestrator error: `{type(e).__name__}: {e}`",
                author="System",
            ).send()
            return

        # Render trace
        await _render_trace(final, root_step)

    # Render outputs (file downloads, summary)
    await _render_final_output(final)


# ============================================================
# Trace rendering (Decision Trace expandable)
# ============================================================
async def _render_trace(state: TPMState, parent_step: cl.Step) -> None:
    """Render handoff packets as nested steps in Chainlit."""
    summary_lines = []
    summary_lines.append(f"**Phase:** `{state.phase.value}`")
    if state.intent:
        summary_lines.append(
            f"**Intent:** {state.intent.action} | {state.intent.subject} | "
            f"conf={state.intent.confidence:.2f}"
        )
    summary_lines.append(f"**Handoff packets:** {len(state.handoff_log)}")

    parent_step.output = "\n".join(summary_lines)

    # Per-packet sub-steps
    for packet in state.handoff_log:
        pdict = packet.model_dump()
        async with cl.Step(name=pdict["stage"], type="tool") as s:
            s.input = pdict.get("payload", {})
            s.output = fmt_handoff(pdict)


# ============================================================
# Final output (downloadable files + diff/summary)
# ============================================================
async def _render_final_output(state: TPMState) -> None:
    if state.phase == OrchestratorPhase.FAILED:
        await cl.Message(
            content=f"❌ **Failed**\n\n```\n{state.error}\n```",
            author="System",
        ).send()
        return

    # No worker output - just show search results
    if not state.final_output:
        return

    fout = state.final_output

    # Worker output - has output_files
    if fout.get("output_files"):
        elements = []
        for fpath in fout["output_files"]:
            p = Path(fpath)
            if not p.exists():
                continue
            mime = _guess_mime(p)
            elements.append(cl.File(name=p.name, path=str(p), display="inline" if mime.startswith("text") else "side", mime=mime))

        body_lines = [
            f"### 🛠️ Worker output: `{fout.get('worker','?')}`",
            "",
            f"**Summary:** {fout.get('summary','')}",
            "",
        ]

        # Auditor block
        passed = fout.get("auditor_passed", False)
        findings = fout.get("auditor_findings", []) or []
        body_lines.append(f"**Auditor:** {'✅ passed' if passed else '⚠️ findings'}")
        if findings:
            for f in findings:
                body_lines.append(f"- {f}")
        body_lines.append("")

        # Metrics summary
        metrics = fout.get("metrics", {})
        if metrics:
            mtbf = metrics.get("mtbf", {})
            mttr = metrics.get("mttr", {})
            body_lines.append("**Reliability metrics:**")
            body_lines.append(f"- MTBF: `{mtbf.get('mtbf_hours','n/a')}` hours")
            body_lines.append(f"- MTTR mean: `{mttr.get('mttr_min','n/a')}` min")
            body_lines.append(f"- Availability: `{metrics.get('availability_pct','n/a')}%`")
            cost = metrics.get("cost", {})
            if cost.get("total_cost_thb"):
                body_lines.append(f"- Total cost: `{cost['total_cost_thb']:,.2f}` THB")
            body_lines.append("")

        body_lines.append("📎 ไฟล์ output อยู่ในแถบด้านขวา — กดดาวน์โหลดได้เลย")

        await cl.Message(
            content="\n".join(body_lines),
            elements=elements,
            author="TPM AI",
        ).send()
        return

    # Search result (no worker)
    if "search" in fout:
        s = fout["search"]
        body = []
        # If we synthesized an answer, show it FIRST and prominently
        answer = fout.get("answer", "").strip()
        if answer:
            body.append("### 💡 Answer")
            body.append("")
            body.append(answer)
            body.append("")
            body.append("---")
            body.append("")
        body.append(f"### 🔎 Search trail")
        body.append(f"- Provider: `{s.get('provider','?')}`  "
                    f"·  Results: {s.get('n_results',0)}  "
                    f"·  Chain: {' → '.join(s.get('fallback_chain', []) or ['(none)'])}")
        body.append("")
        body.append("**Top sources:**")
        for title in (s.get("all_titles") or [])[:5]:
            body.append(f"- {title}")
        await cl.Message(content="\n".join(body), author="TPM AI").send()
        return


def _guess_mime(p: Path) -> str:
    suffix = p.suffix.lower()
    return {
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".pdf": "application/pdf",
        ".md": "text/markdown",
        ".txt": "text/plain",
        ".json": "application/json",
    }.get(suffix, "application/octet-stream")
