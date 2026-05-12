"""
tests/test_inquiry.py - unit tests for tpm_core.inquiry (Section 8)

Verifies:
  - skip rules (general knowledge, emergency, night cycle)
  - user-specific detection (machine tags, vendor names, Thai/English patterns)
  - question generation (Thai vs English)
  - answer parsing (A/B/C, location hints, direct answers)

No LLM required. Run:
    .venv/Scripts/python.exe tests/test_inquiry.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

# UTF-8 stdout for Thai output on Windows cp1252
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

from tpm_core.inquiry import (  # noqa: E402
    build_inquiry_prompt,
    is_emergency,
    is_night_cycle,
    is_user_specific,
    parse_inquiry_answer,
    should_inquire,
)
from tpm_core.state import Intent  # noqa: E402


# ============================================================
# Mini test framework
# ============================================================
PASS = "[PASS]"
FAIL = "[FAIL]"
_failures: list[str] = []


def check(name: str, cond: bool, detail: str = ""):
    if cond:
        print(f"{PASS} {name}")
    else:
        print(f"{FAIL} {name}  {detail}")
        _failures.append(name)


# ============================================================
# Emergency detection
# ============================================================
def t_emergency():
    check("emergency: ด่วน", is_emergency("เครื่องไหม้! ด่วน"))
    check("emergency: emergency en", is_emergency("EMERGENCY - line down"))
    check("emergency: not for normal", not is_emergency("ขอรายงาน PM ของ Boiler"))


# ============================================================
# Night cycle
# ============================================================
def t_night_cycle():
    os.environ.pop("TPM_NIGHT_MODE", None)
    check("night: off by default", not is_night_cycle())
    os.environ["TPM_NIGHT_MODE"] = "1"
    check("night: on when TPM_NIGHT_MODE=1", is_night_cycle())
    os.environ.pop("TPM_NIGHT_MODE", None)


# ============================================================
# User-specific detection
# ============================================================
def _mk_intent(action="lookup", subject="", scope="", **kw):
    return Intent(action=action, subject=subject, scope=scope, **kw)


def t_user_specific():
    # Machine tag style
    check("us: machine tag B-2",
          is_user_specific(_mk_intent(subject="Boiler #2"), "ตรวจ PM ของ Boiler #2"))
    check("us: machine tag M-101",
          is_user_specific(_mk_intent(subject="M-101"), "M-101 broke down"))

    # Internal vendor
    check("us: MAKINO",
          is_user_specific(_mk_intent(subject="MAKINO V33"), "MAKINO V33 downtime trend"))
    check("us: SHIBAURA",
          is_user_specific(_mk_intent(subject="SHIBAURA"), "SHIBAURA injection mold"))

    # Thai user-specific patterns
    check("us: ของเรา",
          is_user_specific(_mk_intent(), "เครื่องของเรารุ่นล่าสุดคืออะไร"))
    check("us: ใครรับผิดชอบ",
          is_user_specific(_mk_intent(), "ใครรับผิดชอบไลน์ A"))

    # English patterns
    check("us: our line",
          is_user_specific(_mk_intent(), "what is the spec for our line 4"))

    # NEGATIVE: general knowledge should NOT match
    check("us: NOT general knowledge",
          not is_user_specific(_mk_intent(subject="FMEA"), "what is FMEA"))
    check("us: NOT TRIZ principle",
          not is_user_specific(_mk_intent(subject="TRIZ 35"), "TRIZ principle 35 คือ"))


# ============================================================
# should_inquire decision tree
# ============================================================
def t_should_inquire():
    # General knowledge -> skip
    d = should_inquire(
        _mk_intent(action="lookup", subject="FMEA", is_definition=True),
        "what is FMEA",
    )
    check("inquire: skip on is_definition", d.skip and d.reason == "general_knowledge")

    # Standard reference -> skip
    d = should_inquire(
        _mk_intent(subject="ASTM A106", is_standard_reference=True),
        "ASTM A106 spec",
    )
    check("inquire: skip on is_standard_reference",
          d.skip and d.reason == "general_knowledge")

    # Emergency -> skip
    d = should_inquire(_mk_intent(subject="Boiler"), "เครื่องไหม้! ด่วน")
    check("inquire: skip on emergency", d.skip and d.reason == "emergency_mode")

    # Night cycle -> skip
    os.environ["TPM_NIGHT_MODE"] = "1"
    try:
        d = should_inquire(_mk_intent(subject="MAKINO"), "MAKINO downtime")
        check("inquire: skip on night cycle", d.skip and d.reason == "night_cycle")
    finally:
        os.environ.pop("TPM_NIGHT_MODE", None)

    # User-specific -> ASK
    d = should_inquire(
        _mk_intent(action="report", subject="MAKINO V33"),
        "เขียนรายงาน PM ของ MAKINO V33",
    )
    check("inquire: ask on user-specific", d.needed and d.reason == "user_specific")
    check("inquire: target captured", "MAKINO" in d.target_phrase)

    # Generic question -> skip
    d = should_inquire(_mk_intent(action="lookup", subject="bearing"), "ราคา bearing")
    check("inquire: skip on generic", d.skip)


# ============================================================
# Question generation
# ============================================================
def t_build_prompt():
    intent_th = _mk_intent(subject="MAKINO V33", constraints={"language": "th"})
    decision = should_inquire(intent_th, "PM ของ MAKINO V33")
    prompt = build_inquiry_prompt(intent_th, decision)
    check("prompt: Thai question present", "MAKINO V33" in prompt["question"])
    check("prompt: Thai options 3+ choices", len(prompt["options"]) >= 3)
    check("prompt: Thai option A is direct-answer",
          prompt["options"][0].startswith("A)") and "พิมพ์" in prompt["options"][0])

    intent_en = _mk_intent(subject="MAKINO V33", constraints={"language": "en"})
    decision_en = should_inquire(intent_en, "MAKINO V33 PM schedule")
    prompt_en = build_inquiry_prompt(intent_en, decision_en)
    check("prompt: English when language=en",
          "do you have" in prompt_en["question"].lower())


# ============================================================
# Answer parsing
# ============================================================
def t_parse_answer():
    # Option C = search
    p = parse_inquiry_answer("C")
    check("parse: C -> search", p.route == "search")

    p = parse_inquiry_answer("ไม่รู้")
    check("parse: ไม่รู้ -> search", p.route == "search")

    p = parse_inquiry_answer("I don't know")
    check("parse: I don't know -> search", p.route == "search")

    # Option B = location
    p = parse_inquiry_answer("B - raw_data/excel_logs/PM_2026.xlsx")
    check("parse: B + path -> location_provided",
          p.route == "location_provided" and "PM_2026.xlsx" in p.payload)

    p = parse_inquiry_answer("https://portal.skf-thailand.com")
    check("parse: URL -> location_provided",
          p.route == "location_provided" and p.payload.startswith("http"))

    # Option A = direct answer
    p = parse_inquiry_answer("A - last PM was 15 April 2026")
    check("parse: A + text -> user_answered",
          p.route == "user_answered" and "15 April" in p.payload)

    # Free-text answer
    p = parse_inquiry_answer("รอบล่าสุดคือ 15 เมษายน 2026")
    check("parse: free text -> user_answered",
          p.route == "user_answered" and "15" in p.payload)

    # Empty falls through to search
    p = parse_inquiry_answer("")
    check("parse: empty -> search", p.route == "search")


# ============================================================
# Run
# ============================================================
def main() -> int:
    for fn in (
        t_emergency,
        t_night_cycle,
        t_user_specific,
        t_should_inquire,
        t_build_prompt,
        t_parse_answer,
    ):
        print(f"\n--- {fn.__name__} ---")
        fn()

    print()
    if _failures:
        print(f"{FAIL} {len(_failures)} test(s) failed:")
        for f in _failures:
            print(f"  - {f}")
        return 1
    print(f"{PASS} all tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
