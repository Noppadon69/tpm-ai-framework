"""
tests/test_mold_domain.py - tpm_mold + new calc formulas (Section 25)

Covers:
  - defect_catalog: causes_for() exact + alias lookup
  - mold_life: life_rules_for() + next_pm_due + is_overhaul_due
  - materials: material_info() lookup
  - process_spec: check_param() range detection
  - calc library: cooling_time_thumb + projected_area_clamp

No LLM, no SSL.

Run:
    .venv/Scripts/python.exe tests/test_mold_domain.py
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

from tpm_mold import (  # noqa: E402
    InjectionDefect,
    PressDefect,
    analyse,
    causes_for,
    check_param,
    life_rules_for,
    material_info,
)
from tpm_mold.mold_life import is_overhaul_due, next_pm_due  # noqa: E402
from tpm_workers.base import WorkerInput, WorkerType  # noqa: E402
from tpm_workers.calc import FORMULA_LIBRARY, calculate, run_calc_worker  # noqa: E402

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
# Defect catalog
# ============================================================
def t_defects():
    causes = causes_for("flash")
    check("defect: flash 4 causes", causes is not None and len(causes) == 4)
    # First cause is highest priority
    check("defect: flash top cause = clamping",
          "clamping" in causes[0].description.lower())

    causes = causes_for(InjectionDefect.SINK_MARK)
    check("defect: SINK_MARK enum lookup",
          causes is not None and len(causes) >= 4)

    # Thai alias
    causes_th = causes_for("รอยบุ๋ม")
    check("defect: Thai alias 'รอยบุ๋ม' -> sink_mark",
          causes_th == causes_for("sink_mark"))

    # Press defect
    causes = causes_for(PressDefect.BURR)
    check("defect: burr has causes",
          causes is not None and any("clearance" in c.description.lower() for c in causes))

    # Unknown
    check("defect: unknown returns None", causes_for("alien_defect") is None)


# ============================================================
# Mold life
# ============================================================
def t_mold_life():
    rule = life_rules_for("SKD61")
    check("life: SKD61 found", rule is not None)
    check("life: SKD61 PM interval 50k", rule.pm_interval == 50_000)
    check("life: SKD61 overhaul 500k", rule.overhaul_threshold == 500_000)
    check("life: SKD61 hardness range", rule.typical_hardness_hrc == (50, 55))

    # Lowercase / whitespace
    check("life: case-insensitive", life_rules_for("skd11") is not None)
    check("life: unknown returns None", life_rules_for("ALIEN") is None)

    # Family filter
    check("life: SKD11 + injection_mold = None",
          life_rules_for("SKD11", family="injection_mold") is None)
    check("life: SKD11 + press_die = match",
          life_rules_for("SKD11", family="press_die") is not None)

    # PM countdown
    rule = life_rules_for("P20")
    check("life: P20 PM countdown 25000",
          next_pm_due(rule, 5_000) == 25_000)
    check("life: P20 just hit PM",
          next_pm_due(rule, 30_000) == 0)

    # Overhaul
    check("life: SKD61 not overhaul at 100k",
          not is_overhaul_due(life_rules_for("SKD61"), 100_000))
    check("life: SKD61 overhaul at 500k",
          is_overhaul_due(life_rules_for("SKD61"), 500_000))


# ============================================================
# Materials
# ============================================================
def t_materials():
    m = material_info("SKD11")
    check("mat: SKD11 found", m is not None)
    check("mat: SKD11 yield 1900",
          m.yield_strength_mpa == 1900)
    check("mat: SKD11 family", m.family == "tool_steel")

    m = material_info("pp")  # case-insensitive
    check("mat: PP plastic family", m and m.family == "plastic")
    check("mat: PP density ~905", m and approx(m.density_kg_m3, 905, rel=0.01))


# ============================================================
# Process spec
# ============================================================
def t_process_spec():
    # In range
    c = check_param("barrel_temperature", 220)
    check("spec: 220C in range for barrel", c and c.in_range)

    # Below
    c = check_param("barrel_temperature", 150)
    check("spec: 150C below range", c and not c.in_range and c.direction == "low")

    # Above
    c = check_param("mold_temperature", 200)
    check("spec: 200C above mold range",
          c and not c.in_range and c.direction == "high")

    # Unknown param
    check("spec: unknown param returns None",
          check_param("unknown_param", 1) is None)


# ============================================================
# New calc formulas
# ============================================================
def t_calc_cooling_time():
    f = FORMULA_LIBRARY["cooling_time_thumb"]
    # t=3mm -> 2 * 9 = 18 s
    r = calculate(f, {"t": (3, "mm")})
    check("calc: cooling 3mm ~ 18s",
          approx(r.output_value, 18.0, rel=0.05),
          detail=f"got {r.output_value}")


def t_calc_projected_area():
    f = FORMULA_LIBRARY["projected_area_clamp"]
    # F=1e6 N, P=50 MPa -> A = 1e6 / 50e6 = 0.02 m^2
    r = calculate(f, {"F": (1_000_000, "N"), "P": (50, "MPa")})
    check("calc: projected area 0.02 m^2",
          approx(r.output_value, 0.02, rel=0.01),
          detail=f"got {r.output_value}")


def t_calc_e2e_cooling():
    """End-to-end through the worker."""
    with tempfile.TemporaryDirectory() as td:
        inp = WorkerInput(
            worker_type=WorkerType.CALC,
            session_id="test-cool",
            user_request="คำนวณ cooling time สำหรับ wall t=2 mm",
            output_dir=Path(td),
        )
        r = run_calc_worker(inp)
        check("calc-e2e: cooling success", r.success, detail=r.summary)
        # t=2mm -> 2 * 4 = 8 s
        check("calc-e2e: 8 seconds", approx(r.metrics["value"], 8.0, rel=0.05),
              detail=f"got {r.metrics.get('value')}")


# ============================================================
# MoldAnalyseNode
# ============================================================
def t_analyse_basic():
    diag = analyse("Flash")
    check("analyse: defect captured", diag.defect == "Flash")
    check("analyse: causes loaded", len(diag.causes) == 4)
    check("analyse: ranked = causes (no deviations)",
          len(diag.ranked_candidates) == 4)
    check("analyse: no deviations", diag.deviations == [])


def t_analyse_with_deviation():
    diag = analyse(
        "Sink mark",
        process_log={"holding_pressure": 20, "barrel_temperature": 220},
    )
    check("analyse: holding_pressure low detected",
          any(d.param == "holding_pressure" and d.direction == "low"
              for d in diag.deviations))
    check("analyse: barrel_temperature in range (no deviation)",
          not any(d.param == "barrel_temperature" for d in diag.deviations))
    # Top cause should mention holding_pressure (boosted)
    top = diag.ranked_candidates[0]
    check("analyse: deviation-aware rank top = holding_pressure cause",
          "holding_pressure" in top.check_via,
          detail=f"top check_via={top.check_via}")


def t_analyse_overhaul():
    diag = analyse(
        "Flash",
        mold_material="SKD61",
        shot_count=500_000,
    )
    check("analyse: overhaul_due detected", diag.overhaul_due)
    # tool_wear cause should get a boost when overhaul is due
    top_categories = [c.category for c in diag.ranked_candidates[:2]]
    check("analyse: overhaul -> tool_wear in top 2",
          "tool_wear" in top_categories,
          detail=f"top2 categories={top_categories}")


def t_analyse_unknown_defect():
    diag = analyse("alien_defect")
    check("analyse: unknown defect -> empty ranked",
          diag.ranked_candidates == [])
    check("analyse: warning emitted", len(diag.warnings) >= 1)


def t_analyse_summary_format():
    diag = analyse(
        "Sink mark",
        process_log={"holding_pressure": 20},
        mold_material="P20",
        shot_count=25_000,
    )
    summary = diag.summary()
    check("summary: mentions defect", "Sink mark" in summary)
    check("summary: mentions deviation", "holding_pressure" in summary)
    check("summary: mentions Next PM", "Next PM in" in summary)
    check("summary: ranked candidates present", "Ranked candidates" in summary)


# ============================================================
# Run
# ============================================================
def main() -> int:
    for fn in (
        t_defects,
        t_mold_life,
        t_materials,
        t_process_spec,
        t_calc_cooling_time,
        t_calc_projected_area,
        t_calc_e2e_cooling,
        t_analyse_basic,
        t_analyse_with_deviation,
        t_analyse_overhaul,
        t_analyse_unknown_defect,
        t_analyse_summary_format,
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
