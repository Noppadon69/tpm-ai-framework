"""
tests/test_calc_worker.py - Calc worker (Section 11.E)

Verifies:
  - formula picker matches keywords (Thai + English)
  - variable extraction from free-text
  - SymPy substitution + Pint unit conversion
  - ad-hoc expression path (extras["formula"])
  - missing variable handling
  - audit file written

No LLM, no network, no SSL. Safe under Bug #7.

Run:
    .venv/Scripts/python.exe tests/test_calc_worker.py
"""
from __future__ import annotations

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

from tpm_workers.base import WorkerInput, WorkerType  # noqa: E402
from tpm_workers.calc import (  # noqa: E402
    FORMULA_LIBRARY,
    calculate,
    extract_variables,
    pick_formula,
    run_calc_worker,
)

PASS = "[PASS]"
FAIL = "[FAIL]"
_failures: list[str] = []


def check(name: str, cond: bool, detail: str = ""):
    if cond:
        print(f"{PASS} {name}")
    else:
        print(f"{FAIL} {name}  {detail}")
        _failures.append(name)


def approx(a: float, b: float, rel: float = 1e-3) -> bool:
    return abs(a - b) <= rel * max(abs(b), 1.0)


# ============================================================
# Formula picker
# ============================================================
def t_pick_formula():
    check("pick: stress en", pick_formula("compute stress when F=100 A=2") == "stress")
    check("pick: ความเค้น th", pick_formula("คำนวณความเค้น F=1000 A=0.05") == "stress")
    check("pick: pressure",   pick_formula("ความดันถ้า F=200 N A=0.01") == "pressure")
    check("pick: ohm's law",  pick_formula("ohm's law I=2 R=10") == "ohms_law")
    check("pick: clamping",   pick_formula("clamping force ของ mold") == "clamping_force")
    check("pick: nothing",    pick_formula("how are you") is None)
    # Regression test for soak-discovered bug 2026-05-12: LLM-hallucinated
    # intent.scope must NOT steer the picker; only user text + subject feed it.
    check("pick: ignore scope hallucination",
          pick_formula(
              "clamping force P=100 MPa A=0.01 m^2",
              intent={"subject": "clamping force P=100 MPa A=0.01 m^2",
                      "scope": "calculate stress"},
          ) == "clamping_force")
    # Multi-word keyword should outscore single-word mention
    check("pick: multi-word wins tie",
          pick_formula("clamping force computation, stress mentioned") == "clamping_force")


# ============================================================
# Variable extraction
# ============================================================
def t_extract():
    v = extract_variables("F=1000 N, A = 0.05 m^2")
    check("extract: F captured", "F" in v and approx(v["F"][0], 1000.0))
    check("extract: F unit",     v["F"][1] == "N")
    check("extract: A captured", "A" in v and approx(v["A"][0], 0.05))

    v = extract_variables("rho=7850 kg/m^3 V=0.001 m^3")
    check("extract: rho",        approx(v["rho"][0], 7850))
    check("extract: rho unit",   v["rho"][1] == "kg/m**3")

    v = extract_variables("I=2A R=10ohm")
    check("extract: I=2",        approx(v["I"][0], 2.0))
    check("extract: R=10ohm",    approx(v["R"][0], 10.0))

    v = extract_variables("scientific F=1.5e3 N")
    check("extract: sci notation", approx(v["F"][0], 1500))

    v = extract_variables("no equations here")
    check("extract: empty", v == {})


# ============================================================
# Calculate
# ============================================================
def t_calc_stress():
    f = FORMULA_LIBRARY["stress"]
    r = calculate(f, {"F": (1000, "N"), "A": (0.05, "m**2")})
    # stress = 1000 / 0.05 = 20000 Pa
    check("calc: stress value", approx(r.output_value, 20000.0),
          detail=f"got {r.output_value}")
    check("calc: stress unit", r.output_unit == "pascal")
    check("calc: no missing", not r.missing_vars)


def t_calc_ohms():
    f = FORMULA_LIBRARY["ohms_law"]
    r = calculate(f, {"I": (2, "A"), "R": (10, "ohm")})
    check("calc: V = 20", approx(r.output_value, 20.0))


def t_calc_unit_conversion():
    """Input in mm^2, formula expects m^2 -> Pint should convert."""
    f = FORMULA_LIBRARY["stress"]
    r = calculate(f, {"F": (1000, "N"), "A": (500, "mm**2")})
    # 500 mm^2 = 0.0005 m^2, stress = 1000 / 0.0005 = 2,000,000 Pa
    check("calc: unit-converted stress",
          approx(r.output_value, 2_000_000.0, rel=1e-3),
          detail=f"got {r.output_value}")


def t_calc_missing():
    f = FORMULA_LIBRARY["stress"]
    r = calculate(f, {"F": (1000, "N")})  # missing A
    check("calc: missing flagged", r.missing_vars == ["A"])


def t_calc_clamping():
    f = FORMULA_LIBRARY["clamping_force"]
    # P=100 MPa, A=0.01 m^2 -> F = 100e6 * 0.01 = 1,000,000 N
    r = calculate(f, {"P": (100, "MPa"), "A": (0.01, "m**2")})
    check("calc: clamping force", approx(r.output_value, 1_000_000.0))


# ============================================================
# Worker entry point
# ============================================================
def t_worker_e2e_library():
    """End-to-end: pick formula from text + extract vars + calc + audit."""
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        inp = WorkerInput(
            worker_type=WorkerType.CALC,
            session_id="test-stress",
            user_request="คำนวณความเค้น F=1000 N A=0.05 m^2",
            output_dir=out,
        )
        result = run_calc_worker(inp)
        check("worker: success",     result.success, detail=result.summary)
        check("worker: file",        len(result.output_files) == 1)
        check("worker: file exists", Path(result.output_files[0]).exists())
        check("worker: value 20000", approx(result.metrics["value"], 20000.0),
              detail=f"got {result.metrics.get('value')}")
        text = Path(result.output_files[0]).read_text(encoding="utf-8")
        check("worker: audit has formula", "Stress" in text or "stress" in text)


def t_worker_e2e_adhoc():
    """Ad-hoc expression path."""
    with tempfile.TemporaryDirectory() as td:
        inp = WorkerInput(
            worker_type=WorkerType.CALC,
            session_id="test-adhoc",
            user_request="evaluate this",
            output_dir=Path(td),
            extras={
                "formula": "x**2 + y",
                "values": {"x": 3, "y": 1},
            },
        )
        result = run_calc_worker(inp)
        check("worker-adhoc: success", result.success, detail=result.summary)
        check("worker-adhoc: 3^2+1=10", approx(result.metrics["value"], 10.0))


def t_worker_no_formula():
    """No keywords match + no ad-hoc -> failure with helpful message."""
    with tempfile.TemporaryDirectory() as td:
        inp = WorkerInput(
            worker_type=WorkerType.CALC,
            session_id="test-nomatch",
            user_request="how are you doing today",
            output_dir=Path(td),
        )
        result = run_calc_worker(inp)
        check("worker-no-formula: failed", not result.success)
        check("worker-no-formula: helpful summary",
              "library" in result.summary.lower() or "formula" in result.summary.lower())


def t_worker_missing_vars():
    """Formula matched but variables missing -> partial success with diagnostics."""
    with tempfile.TemporaryDirectory() as td:
        inp = WorkerInput(
            worker_type=WorkerType.CALC,
            session_id="test-missing",
            user_request="compute stress when F=1000 N",  # A missing
            output_dir=Path(td),
        )
        result = run_calc_worker(inp)
        check("worker-missing: failed", not result.success)
        check("worker-missing: A flagged",
              "A" in (result.metrics.get("missing_vars") or []),
              detail=str(result.metrics))


# ============================================================
# Run
# ============================================================
def main() -> int:
    for fn in (
        t_pick_formula,
        t_extract,
        t_calc_stress,
        t_calc_ohms,
        t_calc_unit_conversion,
        t_calc_missing,
        t_calc_clamping,
        t_worker_e2e_library,
        t_worker_e2e_adhoc,
        t_worker_no_formula,
        t_worker_missing_vars,
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
