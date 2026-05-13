"""
tests/test_tool_registry.py - unit tests for tpm_tools.registry (Phase 3 Day 5)

Run:
    .venv/Scripts/python.exe tests/test_tool_registry.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

from tpm_tools.registry import ToolEntry, ToolRegistry  # noqa: E402

PASS = "[PASS]"
FAIL = "[FAIL]"
_failures: list[str] = []


def check(name: str, cond: bool, detail: str = ""):
    if cond:
        print(f"{PASS} {name}")
    else:
        print(f"{FAIL} {name}  {detail}")
        _failures.append(name)


SAMPLE = {
    "schema_version": "1.1",
    "tools": [
        {
            "id": "report.docx",
            "action": "report",
            "name": "Report",
            "module": "tpm_workers.report",
            "entry_point": "run_report_worker",
            "capabilities": ["docx"],
            "classification_allowed": ["PUBLIC", "INTERNAL"],
            "priority": 10,
        },
        {
            "id": "calc.sympy",
            "action": "calc",
            "name": "Calc",
            "module": "tpm_workers.calc",
            "entry_point": "run_calc_worker",
            "capabilities": ["formula", "stress"],
            "classification_allowed": ["PUBLIC", "INTERNAL", "CONFIDENTIAL"],
            "priority": 10,
        },
        {
            "id": "fallback.analyze",
            "action": "analyze",
            "name": "Fallback",
            "module": "tpm_workers.report",
            "entry_point": "run_report_worker",
            "capabilities": ["analysis"],
            "classification_allowed": ["PUBLIC", "INTERNAL"],
            "priority": 1,
            "is_fallback": True,
        },
    ],
}


def t_load_from_file():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "reg.json"
        p.write_text(json.dumps(SAMPLE), encoding="utf-8")
        reg = ToolRegistry.from_file(p)
        check("load: 3 entries", len(reg.entries) == 3)
        check("load: get by id", reg.get("calc.sympy") is not None)
        check("load: actions", set(reg.list_actions()) == {"report", "calc", "analyze"})


def t_get_for_action_exact():
    reg = ToolRegistry([ToolEntry(**t) for t in SAMPLE["tools"]])
    e = reg.get_for_action("report")
    check("action: exact match", e is not None and e.id == "report.docx")
    e = reg.get_for_action("calc")
    check("action: calc match", e is not None and e.id == "calc.sympy")


def t_get_for_action_unknown_falls_back():
    reg = ToolRegistry([ToolEntry(**t) for t in SAMPLE["tools"]])
    e = reg.get_for_action("unknown_action_xyz")
    check("action: unknown returns fallback",
          e is not None and e.id == "fallback.analyze")


def t_classification_filter():
    reg = ToolRegistry([ToolEntry(**t) for t in SAMPLE["tools"]])
    # Only calc allows CONFIDENTIAL
    e = reg.get_for_action("calc", classification="CONFIDENTIAL")
    check("class: calc OK on CONFIDENTIAL", e is not None and e.id == "calc.sympy")
    e = reg.get_for_action("report", classification="CONFIDENTIAL")
    check("class: report blocked on CONFIDENTIAL", e is None)


def t_capabilities_boost():
    reg = ToolRegistry([ToolEntry(**t) for t in SAMPLE["tools"]])
    # Calc has 'stress' in capabilities; passing the hint should boost it.
    # Action=calc matches exactly anyway, so test the boost on a tie with
    # the fallback's analysis capability.
    e_with = reg.get_for_action("analyze", capabilities_hint=["analysis"])
    check("cap: hint matches keeps fallback",
          e_with is not None and e_with.id == "fallback.analyze")


def t_malformed_entry_skipped():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "reg.json"
        broken = {"schema_version": "1.1",
                  "tools": [
                      {"id": "ok", "action": "x", "name": "X",
                       "module": "tpm_workers.report",
                       "entry_point": "run_report_worker"},
                      {"id": "bad"},  # missing required fields
                  ]}
        p.write_text(json.dumps(broken), encoding="utf-8")
        reg = ToolRegistry.from_file(p)
        check("malformed: only valid loaded", len(reg.entries) == 1)


def t_missing_file_empty_registry():
    reg = ToolRegistry.from_file("/does/not/exist/reg.json")
    check("missing-file: empty registry", len(reg.entries) == 0)


def t_resolve_callable():
    """ToolEntry.resolve() should return the actual Python function."""
    e = ToolEntry(
        id="calc.test", action="calc", name="t",
        module="tpm_workers.calc", entry_point="run_calc_worker",
    )
    fn = e.resolve()
    check("resolve: returns callable", callable(fn))


def t_real_registry_loads():
    """The repo's real .tpm_context/tool_registry.json must parse without errors."""
    from tpm_tools.registry import default_registry, reload
    reload()
    reg = default_registry()
    check("real: >=4 entries", len(reg.entries) >= 4)
    check("real: report entry present", reg.get("report.docx") is not None)
    check("real: calc entry resolves",
          reg.get("calc.sympy") is not None and callable(reg.get("calc.sympy").resolve()))
    check("real: vision entry present", reg.get("vision.qwen25vl") is not None)


def main() -> int:
    for fn in (
        t_load_from_file,
        t_get_for_action_exact,
        t_get_for_action_unknown_falls_back,
        t_classification_filter,
        t_capabilities_boost,
        t_malformed_entry_skipped,
        t_missing_file_empty_registry,
        t_resolve_callable,
        t_real_registry_loads,
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
