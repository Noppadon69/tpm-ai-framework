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
        """Render an interactive ask via cl.AskActionMessage when possible."""
        # Build action buttons from the option list (skip the free-form 'อื่นๆ')
        actions: list[cl.Action] = []
        for opt in options:
            stripped = opt.strip()
            if not stripped:
                continue
            # Free-form escape - render as a hint, not a button
            if any(token in stripped.lower() for token in ("อื่นๆ", "พิมพ์", "type", "describe")):
                continue
            label = stripped[:60]
            actions.append(
                cl.Action(
                    name="opt",
                    value=stripped,
                    label=label,
                    payload={"value": stripped},
                )
            )

        if actions:
            res = await cl.AskActionMessage(
                content=f"❓ **{question}**\n\nเลือกตัวเลือก หรือพิมพ์อธิบายเพิ่มในข้อความถัดไป:",
                actions=actions,
                timeout=self._ask_timeout_s,
            ).send()
            if res and isinstance(res, dict):
                payload = res.get("payload", {})
                value = payload.get("value") or res.get("value") or ""
                if value:
                    return str(value)
                return ""
            # No action chosen - fall through to free-form prompt
        # Pure free-form question
        msg = await cl.AskUserMessage(
            content=f"❓ **{question}**\n\n" + "\n".join(options),
            timeout=self._ask_timeout_s,
        ).send()
        if msg and isinstance(msg, dict):
            return str(msg.get("output", ""))
        return ""

    async def _async_info(self, msg: str) -> None:
        await cl.Message(content=msg, author="TPM AI").send()


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
