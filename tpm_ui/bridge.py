"""
tpm_ui.bridge - sync-async UI bridge for Chainlit

The orchestrator is synchronous (LangGraph), but Chainlit handlers are async.
This bridge runs the orchestrator in a worker thread and pipes UI calls
(ask, info) back to the Chainlit event loop via run_coroutine_threadsafe.
"""
from __future__ import annotations

import asyncio
import logging
from concurrent.futures import Future
from typing import Optional

import chainlit as cl

from tpm_core.orchestrator import UI

log = logging.getLogger(__name__)


class ChainlitUI(UI):
    """
    Implements the orchestrator UI contract using Chainlit primitives.

    Lifecycle:
        Created in Chainlit handler (async context).
        Captured event_loop -> orchestrator runs in thread -> ui.ask()/info()
        marshal back to event_loop via run_coroutine_threadsafe.

    Threading model:
        - orchestrator thread = blocked when calling .ask() until user responds
        - chainlit thread = handles input/output normally
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
        Render question with options as TEXT (not action buttons), so user can
        either type the option label/letter OR write a free-form description.

        Why not AskActionMessage? It blocks the chat input box, so users who
        want to type instead of clicking get stuck. AskUserMessage always
        accepts free-form input.
        """
        clean_options = [o.strip() for o in options if o.strip()]
        body_lines = [f"❓ **{question}**"]
        if clean_options:
            body_lines.append("")
            for opt in clean_options:
                body_lines.append(f"  • {opt}")
            body_lines.append("")
            body_lines.append(
                "💬 _พิมพ์ตัวเลือก (เช่น A) หรือพิมพ์อธิบายเพิ่มเติมก็ได้_"
            )

        msg = await cl.AskUserMessage(
            content="\n".join(body_lines),
            timeout=self._ask_timeout_s,
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
    if upper not in {"A", "B", "C", "D", "E"}:
        return answer
    idx = "ABCDE".index(upper)
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
