"""
test_bug6_fallback.py - Bug #6 permanent-fallback unit tests.

Verifies that when chat_json raises (timeout, network, JSON error),
parse_intent returns a schema-valid intent dict from the deterministic
rule-based fallback instead of crashing.

No LLM, no network, no SSL. Safe under Bug #7.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# sitecustomize.py auto-inserts the main checkout (~/.venv/.../sitecustomize.py
# from venv parents[3]) ahead of our worktree path, which would mask the
# worktree's tpm_core when running from a worktree. Evict any cached tpm_core
# modules so the fresh sys.path.insert above wins.
for _m in [k for k in list(sys.modules) if k == "tpm_core" or k.startswith("tpm_core.")]:
    del sys.modules[_m]

# Bug #7 env scrub before any SSL imports
import tpm_core._envfix  # noqa: F401, E402

from tpm_core import clarification as clar  # noqa: E402

# Verify we got the worktree copy
assert str(REPO_ROOT) in clar.__file__, (
    f"loaded wrong clarification.py: {clar.__file__}\n"
    f"expected to start with: {REPO_ROOT}\n"
    f"sys.path[:3]: {sys.path[:3]}"
)


PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"[PASS] {name}{(' - ' + detail) if detail else ''}")
    else:
        FAIL += 1
        print(f"[FAIL] {name}  {detail}")


# --------------------------------------------------------------------------
# Tier 1 - direct fallback unit tests (no LLM mock needed)
# --------------------------------------------------------------------------

def t_lookup_definition() -> None:
    out = clar._fallback_intent_from_rules(["FMEA vs FTA ต่างกันยังไง"])
    check("lookup-def: action", out["action"] == "lookup")
    check("lookup-def: is_definition", out["is_definition"] is True)
    check("lookup-def: confidence <= 0.55", out["confidence"] <= 0.55)
    check("lookup-def: _fallback marker", out.get("_fallback") is True)
    check("lookup-def: schema-required keys",
          all(k in out for k in ("action", "subject", "scope", "confidence",
                                 "missing", "alternatives")))


def t_excel_action() -> None:
    out = clar._fallback_intent_from_rules(["ออกเป็น Excel ของ MAKINO-a51nx"])
    check("excel: action", out["action"] == "excel")
    check("excel: subject ALL-CAPS code preferred",
          out["subject"] == "MAKINO", detail=f"got {out['subject']!r}")


def t_report_action() -> None:
    out = clar._fallback_intent_from_rules(["เขียนรายงาน SHIBAURA-EC100SX"])
    check("report: action", out["action"] == "report")
    check("report: subject is engineering code",
          out["subject"].startswith("SHIBAURA"))


def t_vision_action() -> None:
    out = clar._fallback_intent_from_rules(["ดูรูปนี้ให้หน่อย"])
    check("vision: action", out["action"] == "vision")


def t_calc_action() -> None:
    out = clar._fallback_intent_from_rules(["คำนวณ stress ของ punch"])
    check("calc: action", out["action"] == "calc")


def t_analyze_action() -> None:
    out = clar._fallback_intent_from_rules(["pareto chart of downtime"])
    check("analyze: action", out["action"] == "analyze")


def t_default_lookup_safest() -> None:
    out = clar._fallback_intent_from_rules(["MAKINO a51nx"])
    check("default: falls through to lookup (egress-safe)",
          out["action"] == "lookup")
    check("default: low confidence (<= 0.35)", out["confidence"] <= 0.35)


def t_empty_history() -> None:
    out = clar._fallback_intent_from_rules([])
    check("empty: still returns schema dict", isinstance(out, dict))
    check("empty: confidence > 0", out["confidence"] > 0)
    check("empty: subject empty + missing flagged",
          out["subject"] == "" and "subject" in out["missing"])


def t_subject_extraction_machine_code() -> None:
    s = clar._extract_fallback_subject("repair M-101 mold today")
    check("subject-extract: prefers M-101 code", s == "M-101", detail=f"got {s!r}")


def t_subject_extraction_no_code() -> None:
    s = clar._extract_fallback_subject("repair the broken pump now")
    check("subject-extract: longest non-stop token",
          s in ("broken", "repair", "pump"), detail=f"got {s!r}")


# --------------------------------------------------------------------------
# Tier 2 - parse_intent wrapper integration (mocked chat_json failures)
# --------------------------------------------------------------------------

def t_parse_intent_timeout_falls_back() -> None:
    """When chat_json raises (e.g. timeout), parse_intent must NOT crash."""
    with patch.object(clar, "chat_json", side_effect=TimeoutError("simulated 60s timeout")):
        out = clar.parse_intent("tpm-orch:latest", ["FMEA vs FTA ต่างกันยังไง"])
    check("wrapper-timeout: returns dict not exception", isinstance(out, dict))
    check("wrapper-timeout: fallback marker set", out.get("_fallback") is True)
    check("wrapper-timeout: lookup classification", out["action"] == "lookup")
    check("wrapper-timeout: is_definition True",
          out.get("is_definition") is True)


def t_parse_intent_json_error_falls_back() -> None:
    """When chat_json raises ValueError (parse fail), fallback kicks in."""
    with patch.object(clar, "chat_json", side_effect=ValueError("bad json")):
        out = clar.parse_intent("tpm-orch:latest", ["ออกเป็น Excel ของ MAKINO"])
    check("wrapper-json-err: returns dict not exception", isinstance(out, dict))
    check("wrapper-json-err: excel classification", out["action"] == "excel")


def t_parse_intent_runtime_error_falls_back() -> None:
    """RuntimeError from chat_json (network exhausted retries) -> fallback."""
    with patch.object(clar, "chat_json", side_effect=RuntimeError("ollama unreachable")):
        out = clar.parse_intent("tpm-orch:latest", ["random query"])
    check("wrapper-rt-err: returns dict not exception", isinstance(out, dict))
    check("wrapper-rt-err: default lookup fallback",
          out["action"] == "lookup" and out.get("_fallback") is True)


def t_parse_intent_success_passes_through() -> None:
    """When LLM succeeds, parse_intent returns its dict unchanged (no fallback)."""
    fake_llm_response = {
        "action": "report", "subject": "M-101", "scope": "weekly PM",
        "confidence": 0.92, "constraints": {}, "missing": [],
        "alternatives": [], "is_definition": False,
        "is_standard_reference": False, "needs_grounding": False,
    }
    with patch.object(clar, "chat_json", return_value=fake_llm_response):
        out = clar.parse_intent("tpm-orch:latest", ["weekly PM ของ M-101"])
    check("wrapper-success: LLM result returned as-is",
          out["action"] == "report" and out["confidence"] == 0.92)
    check("wrapper-success: no _fallback marker",
          out.get("_fallback") is None)


# --------------------------------------------------------------------------
# Run
# --------------------------------------------------------------------------

def main() -> int:
    print("=" * 60)
    print("Bug #6 permanent-fallback tests")
    print("=" * 60)

    t_lookup_definition()
    t_excel_action()
    t_report_action()
    t_vision_action()
    t_calc_action()
    t_analyze_action()
    t_default_lookup_safest()
    t_empty_history()
    t_subject_extraction_machine_code()
    t_subject_extraction_no_code()

    t_parse_intent_timeout_falls_back()
    t_parse_intent_json_error_falls_back()
    t_parse_intent_runtime_error_falls_back()
    t_parse_intent_success_passes_through()

    print("-" * 60)
    if FAIL == 0:
        print(f"[PASS] all tests passed  ({PASS} assertions)")
        return 0
    print(f"[FAIL] {FAIL} failed / {PASS} passed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
