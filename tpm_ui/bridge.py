"""
tpm_ui.bridge - sync-async UI bridge for Chainlit

The orchestrator is synchronous (LangGraph), but Chainlit handlers are async.
This bridge runs the orchestrator in a worker thread and pipes UI calls
(ask, info) back to the Chainlit event loop via run_coroutine_threadsafe.

Question/answer routing:
    Each ui.ask() creates an asyncio.Queue stored in cl.user_session.
    Both the @cl.action_callback (button clicks) AND on_message (free-form
    text) route their input to that queue while 'awaiting_answer' is True.
    This way users can EITHER click buttons OR type — both work.
"""
from __future__ import annotations

import asyncio
import logging
from concurrent.futures import Future
from typing import Optional

import chainlit as cl

from tpm_core.orchestrator import UI

log = logging.getLogger(__name__)

# Action name used for clarification choice buttons (must match @cl.action_callback)
CLARIFY_ACTION_NAME = "tpm_clarify_choice"


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
        Send a regular cl.Message with action buttons attached.
        User can EITHER click an action OR type free-form text.
        Both paths feed into the same per-session asyncio.Queue.
        """
        clean_options = [o.strip() for o in options if o.strip()]

        # Per-session queue + awaiting flag (read by app.on_message + action_callback)
        queue: asyncio.Queue[str] = asyncio.Queue()
        cl.user_session.set("ask_queue", queue)
        cl.user_session.set("ask_options", clean_options)
        cl.user_session.set("awaiting_answer", True)

        # Render
        body_lines = [f"❓ **{question}**"]
        if clean_options:
            body_lines.append("")
            body_lines.append("_เลือกปุ่มข้างล่าง หรือพิมพ์อธิบายเองก็ได้_")

        # Build action buttons (Chainlit shows them under the message)
        actions: list[cl.Action] = []
        for i, opt in enumerate(clean_options):
            label = opt[:60]
            actions.append(
                cl.Action(
                    name=CLARIFY_ACTION_NAME,
                    value=opt,
                    label=label,
                    payload={"value": opt, "index": i},
                )
            )

        msg = cl.Message(
            content="\n".join(body_lines),
            actions=actions or None,
            author="TPM AI",
        )
        await msg.send()

        # Wait for either a button click or a typed message
        try:
            answer = await asyncio.wait_for(queue.get(), timeout=self._ask_timeout_s)
        except asyncio.TimeoutError:
            log.warning("ChainlitUI.ask timed out after %.0fs", self._ask_timeout_s)
            answer = ""
        finally:
            cl.user_session.set("awaiting_answer", False)
            cl.user_session.set("ask_queue", None)
            cl.user_session.set("ask_options", None)

        return _expand_letter_choice(answer, clean_options)

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
