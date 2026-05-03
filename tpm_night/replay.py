"""
tpm_night.replay - re-run a saved session, optionally with a deeper model
ref: MASTER_PLAN_v5.md § 15.2

Strategy:
    Original session ran on Qwen3-8B (fast, daytime).
    Night replay reuses the same user_request but with:
      - same model      -> reproducibility check
      - heavier model   -> see if a smarter model would have answered differently
      - same model + clean prompt -> isolate prompt drift
    Skip clarification (use the saved confirmed intent directly).
"""
from __future__ import annotations

import logging
from typing import Optional

from tpm_night.session_store import SessionRecord

log = logging.getLogger(__name__)


# ============================================================
# Headless UI - feeds saved answers back to the orchestrator
# ============================================================
class ReplayUI:
    """
    Implements the orchestrator UI contract for headless replay.
    - ask(): always returns "yes" (auto-confirm intent)
            because we trust the saved confirmed intent
    - info(): logs to debug
    """

    def __init__(self, label: str = "replay"):
        self.label = label
        self.questions_asked = 0
        self.info_messages: list[str] = []

    def ask(self, question: str, options: list[str]) -> str:
        self.questions_asked += 1
        # In replay we never re-ask - just confirm intent
        # (orchestrator's clarify_node treats "yes"/"y"/"" as proceed)
        return "yes"

    def info(self, msg: str) -> None:
        self.info_messages.append(msg)
        log.debug("[%s] %s", self.label, msg)


# ============================================================
# Replay one session
# ============================================================
def replay_session(
    rec: SessionRecord,
    *,
    model: Optional[str] = None,
    persist: bool = False,
):
    """
    Re-run rec.user_request and return the new final TPMState.
    `model=None` -> use rec.model_name (reproducibility check)
    `model="qwen3:14b"` -> heavier model challenge (run on CPU+GPU split)
    """
    # Lazy imports to avoid cycles
    from tpm_core.orchestrator import build_graph, DEFAULT_MODEL
    from tpm_core.state import TPMState

    target_model = model or rec.model_name or DEFAULT_MODEL
    log.info(
        "replay session=%s model=%s request=%r",
        rec.session_id, target_model, rec.user_request[:60],
    )

    ui = ReplayUI(label=f"replay-{rec.session_id[:6]}")
    graph = build_graph(ui=ui, model=target_model)

    initial = TPMState(
        user_request=rec.user_request,
        model_name=target_model,
    )
    # Pre-fill confirmed intent so clarify_node short-circuits to PLAN
    if rec.intent and rec.intent.get("confidence", 0.0) >= 0.5:
        from tpm_core.state import Intent
        try:
            initial.intent = Intent(**rec.intent)
            # Bump confidence to skip the clarification dialog
            initial.intent.confidence = max(initial.intent.confidence, 0.95)
            initial.clarify_history = list(rec.intent.get("history", []) or [rec.user_request])
        except Exception as e:  # noqa: BLE001
            log.warning("could not restore intent: %s", e)

    started_at = initial.started_at
    try:
        final = graph.invoke(initial)
    except Exception as e:  # noqa: BLE001
        log.error("replay invoke failed: %s", e)
        return None
    if isinstance(final, dict):
        final = TPMState(**final)

    # Optional: persist replay too (default False to avoid duplicates)
    if persist:
        try:
            from tpm_night.session_store import save_session
            save_session(final, started_at=started_at)
        except Exception as e:  # noqa: BLE001
            log.warning("replay persistence failed: %s", e)
    return final
