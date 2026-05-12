"""
tests/test_inquiry_node.py - integration test for the inquiry NODE in the
LangGraph orchestrator. Verifies the node transitions and state mutation
WITHOUT going through clarify (= no LLM call, no SSL needed).

This complements tests/test_inquiry.py (pure unit) and tests/test_orchestrator_flow.py
(end-to-end with LLM). Useful when Bug #7 (OPENSSL_Uplink) blocks the e2e suite.

Run:
    .venv/Scripts/python.exe tests/test_inquiry_node.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

from tpm_core.orchestrator import UI, make_inquiry_node  # noqa: E402
from tpm_core.state import Intent, OrchestratorPhase, TPMState  # noqa: E402


class RecordingUI(UI):
    def __init__(self, answer: str = "C"):
        self.answer = answer
        self.questions: list[tuple[str, list[str]]] = []
        self.infos: list[str] = []

    def ask(self, question: str, options: list[str]) -> str:
        self.questions.append((question, list(options)))
        return self.answer

    def info(self, msg: str) -> None:
        self.infos.append(msg)


PASS = "[PASS]"
FAIL = "[FAIL]"
_failures: list[str] = []


def check(name: str, cond: bool, detail: str = ""):
    if cond:
        print(f"{PASS} {name}")
    else:
        print(f"{FAIL} {name}  {detail}")
        _failures.append(name)


def t_skip_on_definition():
    """is_definition=True -> inquiry skipped, route=skipped."""
    ui = RecordingUI()
    node = make_inquiry_node(ui)
    state = TPMState(
        user_request="what is FMEA",
        intent=Intent(action="lookup", subject="FMEA", is_definition=True),
        phase=OrchestratorPhase.INQUIRY,
    )
    out = node(state)
    check("skip-def: phase=PLAN", out.phase == OrchestratorPhase.PLAN)
    check("skip-def: route=skipped", out.inquiry_route == "skipped")
    check("skip-def: no question asked", len(ui.questions) == 0)
    check("skip-def: reason=general_knowledge",
          out.inquiry_skip_reason == "general_knowledge")


def t_skip_on_emergency():
    ui = RecordingUI()
    node = make_inquiry_node(ui)
    state = TPMState(
        user_request="ด่วน! Boiler ไหม้!",
        intent=Intent(action="report", subject="Boiler B-2"),
        phase=OrchestratorPhase.INQUIRY,
    )
    out = node(state)
    check("skip-emer: phase=PLAN", out.phase == OrchestratorPhase.PLAN)
    check("skip-emer: route=skipped", out.inquiry_route == "skipped")
    check("skip-emer: reason=emergency_mode",
          out.inquiry_skip_reason == "emergency_mode")
    check("skip-emer: no question asked", len(ui.questions) == 0)


def t_skip_on_night_cycle():
    os.environ["TPM_NIGHT_MODE"] = "1"
    try:
        ui = RecordingUI()
        node = make_inquiry_node(ui)
        state = TPMState(
            user_request="MAKINO V33 PM schedule",
            intent=Intent(action="report", subject="MAKINO V33"),
            phase=OrchestratorPhase.INQUIRY,
        )
        out = node(state)
        check("skip-night: phase=PLAN", out.phase == OrchestratorPhase.PLAN)
        check("skip-night: route=skipped", out.inquiry_route == "skipped")
        check("skip-night: reason=night_cycle",
              out.inquiry_skip_reason == "night_cycle")
    finally:
        os.environ.pop("TPM_NIGHT_MODE", None)


def t_ask_on_user_specific_then_search():
    """User-specific + answer 'C' -> route=search."""
    ui = RecordingUI(answer="C")
    node = make_inquiry_node(ui)
    state = TPMState(
        user_request="PM schedule ของ MAKINO V33",
        intent=Intent(action="report", subject="MAKINO V33"),
        phase=OrchestratorPhase.INQUIRY,
    )
    out = node(state)
    check("ask-search: phase=PLAN", out.phase == OrchestratorPhase.PLAN)
    check("ask-search: 1 question asked", len(ui.questions) == 1)
    check("ask-search: route=search", out.inquiry_route == "search")
    check("ask-search: question mentions subject",
          "MAKINO V33" in ui.questions[0][0])


def t_ask_user_answered_folds_into_scope():
    """A) + answer -> route=user_answered, scope appended."""
    ui = RecordingUI(answer="A - last PM was 15 April 2026")
    node = make_inquiry_node(ui)
    intent = Intent(action="report", subject="Boiler #2", scope="quarterly review")
    state = TPMState(
        user_request="PM ของ Boiler #2",
        intent=intent,
        phase=OrchestratorPhase.INQUIRY,
    )
    out = node(state)
    check("ans-fold: route=user_answered", out.inquiry_route == "user_answered")
    check("ans-fold: payload captured",
          out.inquiry_payload and "15 April" in out.inquiry_payload)
    check("ans-fold: scope updated",
          out.intent and "user-provided" in (out.intent.scope or "")
          and "15 April" in out.intent.scope)


def t_location_provided():
    """B + path -> route=location_provided."""
    ui = RecordingUI(answer="B - raw_data/PM_2026.xlsx tab Boiler")
    node = make_inquiry_node(ui)
    state = TPMState(
        user_request="PM ของ Boiler #2",
        intent=Intent(action="report", subject="Boiler #2"),
        phase=OrchestratorPhase.INQUIRY,
    )
    out = node(state)
    check("loc: route=location_provided", out.inquiry_route == "location_provided")
    check("loc: payload has path", "PM_2026.xlsx" in (out.inquiry_payload or ""))


def t_handoff_logged():
    """Inquiry node always emits a HandoffPacket."""
    ui = RecordingUI()
    node = make_inquiry_node(ui)
    state = TPMState(
        user_request="what is FMEA",
        intent=Intent(action="lookup", subject="FMEA", is_definition=True),
        phase=OrchestratorPhase.INQUIRY,
    )
    out = node(state)
    last = out.handoff_log[-1] if out.handoff_log else None
    check("handoff: stage=inquiry", last is not None and last.stage == "inquiry")
    check("handoff: success=True", last is not None and last.success)


def main() -> int:
    for fn in (
        t_skip_on_definition,
        t_skip_on_emergency,
        t_skip_on_night_cycle,
        t_ask_on_user_specific_then_search,
        t_ask_user_answered_folds_into_scope,
        t_location_provided,
        t_handoff_logged,
    ):
        print(f"\n--- {fn.__name__} ---")
        fn()

    print()
    if _failures:
        print(f"{FAIL} {len(_failures)} test(s) failed")
        return 1
    print(f"{PASS} all tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
