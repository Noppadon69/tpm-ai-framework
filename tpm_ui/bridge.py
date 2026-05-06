"""
tpm_ui.bridge - sync-async UI bridge for Chainlit

The orchestrator is synchronous (LangGraph), but Chainlit handlers are async.
This bridge runs the orchestrator in a worker thread and pipes UI calls
(ask, info) back to the Chainlit event loop via run_coroutine_threadsafe.

Strategy: AskUserMessage primitive
    Why? Chainlit's send/stop button state is driven by the framework's own
    "awaiting reply" tracking. cl.Message + actions does NOT register as a
    pause - so the input box stays in "stop" mode and user can't send a new
    message. cl.AskUserMessage IS a known pause primitive: input goes back
    to "send" mode, framework handles routing of the next user reply.
    Trade-off: no clickable action buttons. Options shown as letter-coded
    text bullets; _expand_letter_choice() maps 'A'/'B' -> full option text.
"""
from __future__ import annotations

import asyncio
import logging
from concurrent.futures import Future

import chainlit as cl

from tpm_core.orchestrator import UI

log = logging.getLogger(__name__)


class ChainlitUI(UI):
    """
    Implements the orchestrator UI contract using Chainlit's AskUserMessage.

    Threading model:
        - orchestrator thread = blocks on ask() until user replies
        - chainlit event loop = processes the AskUserMessage cleanly
    """

    def __init__(self, ask_timeout_s: float = 600.0):
        self._loop = asyncio.get_event_loop()
        self._ask_timeout_s = ask_timeout_s

    # ============================================================
    # Sync interface (called from orchestrator thread)
    # ============================================================
    def ask(self, question: str, options: list[str]) -> str:
        """Block orchestrator thread, route question to Chainlit, await user reply."""
        future: Future = asyncio.run_coroutine_threadsafe(
            self._async_ask(question, options),
            self._loop,
        )
        try:
            return future.result(timeout=self._ask_timeout_s)
        except Exception as e:  # noqa: BLE001
            log.error("ChainlitUI.ask timeout/error: %s", e)
            return ""

    def info(self, msg: str) -> None:
        """Fire-and-forget message to Chainlit (don't block orchestrator)."""
        try:
            asyncio.run_coroutine_threadsafe(
                self._async_info(msg),
                self._loop,
            )
        except Exception as e:  # noqa: BLE001
            log.error("ChainlitUI.info error: %s", e)

    # ============================================================
    # Async helpers (run on Chainlit event loop)
    # ============================================================
    async def _async_ask(self, question: str, options: list[str]) -> str:
        """
        Render question + options as letter-coded bullets via AskUserMessage.
        User can:
          - type 'A' / 'B' / 'C' (single letter, fast)
          - type 'yes' / 'no' / 'แก้ไข' (confirm/revise tokens)
          - type free-form description (any other text)
        """
        clean_options = [o.strip() for o in options if o.strip()]
        body_lines = [f"❓ **{question}**"]
        if clean_options:
            body_lines.append("")
            for i, opt in enumerate(clean_options):
                letter = "ABCDEF"[i] if i < 6 else "?"
                body_lines.append(f"  **{letter})** {opt}")
            body_lines.append("")
            body_lines.append(
                "💬 _พิมพ์ตัวอักษร A/B/C เพื่อเลือก หรือพิมพ์อธิบายเอง_"
            )

        msg = await cl.AskUserMessage(
            content="\n".join(body_lines),
            timeout=self._ask_timeout_s,
            author="TPM AI",
        ).send()

        if msg and isinstance(msg, dict):
            answer = str(msg.get("output", "")).strip()
            return _expand_letter_choice(answer, clean_options)
        return ""

    async def _async_info(self, msg: str) -> None:
        await cl.Message(content=msg, author="TPM AI").send()


def _expand_letter_choice(answer: str, options: list[str]) -> str:
    """
    If user typed just 'A'/'B'/'C', expand to the full option text.
    Otherwise return as-is (free-form).
    """
    if not answer or len(answer) > 4:
        return answer
    upper = answer.upper().rstrip(")").rstrip(".").strip()
    if upper not in {"A", "B", "C", "D", "E", "F"}:
        return answer
    idx = "ABCDEF".index(upper)
    if idx < len(options):
        return options[idx]
    return answer


# ============================================================
# Helper: format handoff packets / steps for the trace UI
# ============================================================
def fmt_handoff(packet: dict) -> str:
    stage = packet.get("stage", "?")
    success = packet.get("success", True)
    confidence = packet.get("confidence", 0.0)
    reasoning = packet.get("reasoning", "")
    icon = "✅" if success else "⚠️"
    return f"{icon} **{stage}** (conf={confidence:.2f})\n{reasoning}"
