"""
demo_mold_calc.py - mold + die engineering calc walkthrough

Exercises the existing FORMULA_LIBRARY in tpm_workers/calc.py against four
realistic Toshiba mold/die scenarios. Each scenario:
  1) labels the design question
  2) supplies variables with units
  3) calls calc.calculate() (the deterministic SymPy + Pint engine)
  4) prints unit-aware result + brief engineering interpretation

Output: console table + audit-style Markdown at output/demo/mold_calc.md

No LLM. Pure engineering math. Day-1 talking point: 'these are the four
numbers the supervisor will ask within the first week, and they all come
out unit-checked by Pint.'
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make tpm_workers importable when run from worktree
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
for _m in [k for k in list(sys.modules) if k == "tpm_workers" or k.startswith("tpm_workers.")]:
    del sys.modules[_m]

from tpm_workers.calc import FORMULA_LIBRARY, calculate  # noqa: E402


# ============================================================
# Scenarios (Toshiba washing-machine context)
# ============================================================
SCENARIOS = [
    {
        "title": "Clamping force - drum cover injection (PP, 200 x 150 mm part)",
        "formula_id": "clamping_force",
        "variables": {
            # P = cavity pressure (typical PP = 30-50 MPa); A = projected area
            "P": (40.0, "megapascal"),
            "A": (0.030, "meter**2"),  # 200x150 mm = 0.030 m^2
        },
        "interpret": lambda val_n: (
            f"Selected machine clamping must be > {val_n/1000:.1f} kN. "
            f"A 200-ton machine (1962 kN) gives {1962e3/val_n:.1f}x safety margin."
        ),
    },
    {
        "title": "Shot weight - same drum cover (PP density 0.91 g/cm^3)",
        "formula_id": "shot_weight",
        "variables": {
            "rho": (910.0, "kilogram/meter**3"),  # PP
            "V": (0.00012, "meter**3"),           # 120 cm^3 cavity volume
        },
        "interpret": lambda val_kg: (
            f"Single-shot mass = {val_kg*1000:.1f} g. A 0.5 kg-rated barrel "
            f"covers ~{0.5/val_kg:.1f}x this part."
        ),
    },
    {
        "title": "Cooling time (rule-of-thumb, 3 mm wall)",
        "formula_id": "cooling_time_thumb",
        "variables": {
            # cooling_time_thumb expression = t^2 / (pi^2 * alpha) ; pass t (wall thickness)
            "t": (0.003, "meter"),  # 3 mm wall
        },
        "interpret": lambda val_s: (
            f"~{val_s:.1f} s cooling minimum. With 8 s dwell + 4 s ejection -> "
            f"total cycle ~{val_s + 12:.1f} s; throughput "
            f"{3600/(val_s + 12):.0f} parts/hour."
        ),
    },
    {
        "title": "Punch corner stress (press die analog, 50 kN over 25 mm^2)",
        "formula_id": "stress",
        "variables": {
            "F": (50000.0, "newton"),
            "A": (2.5e-5, "meter**2"),  # 25 mm^2
        },
        "interpret": lambda val_pa: (
            f"sigma = {val_pa/1e6:.0f} MPa. SKD11 yield ~1450 MPa "
            f"(safety {1450e6/val_pa:.1f}x), but stress concentration on "
            f"sharp punch corner can be 2-3x nominal - check fillet radius."
        ),
    },
]


def fmt_value(val: float, unit_str: str) -> str:
    # readable formatting for big/small numbers
    if abs(val) >= 1e6:
        return f"{val/1e6:,.2f} M{unit_str}"
    if abs(val) >= 1e3:
        return f"{val:,.1f} {unit_str}"
    if abs(val) >= 1.0:
        return f"{val:,.3f} {unit_str}"
    return f"{val:.4g} {unit_str}"


def run() -> int:
    out_dir = Path("output/demo")
    out_dir.mkdir(parents=True, exist_ok=True)
    md_lines: list[str] = ["# Mold/die calc demo - Toshiba washing-machine context", ""]

    print("=" * 64)
    print("Mold + die engineering calc walkthrough")
    print("=" * 64)

    for sc in SCENARIOS:
        formula = FORMULA_LIBRARY[sc["formula_id"]]
        result = calculate(formula, sc["variables"])

        print(f"\n[{sc['title']}]")
        print(f"  formula : {formula.name_en}  ->  {formula.expression}")
        for var, (value, unit) in sc["variables"].items():
            print(f"  input   : {var} = {value} {unit}")

        if result.missing_vars or not result.dim_check_ok:
            err = f"missing={result.missing_vars} dim_ok={result.dim_check_ok}"
            print(f"  ERROR   : {err}")
            md_lines += [
                f"## {sc['title']}",
                "",
                f"- Formula: `{formula.expression}` ({formula.name_en})",
                f"- ERROR: {err}",
                "",
            ]
            continue

        val = result.output_value
        readable = fmt_value(val, result.output_unit)
        print(f"  result  : {readable}  (raw value = {val:.6g})")
        for w in result.warnings:
            print(f"  warn    : {w}")
        try:
            interp = sc["interpret"](val)
            print(f"  notes   : {interp}")
        except Exception as e:  # noqa: BLE001
            interp = f"(interpretation skipped: {e})"

        md_lines += [
            f"## {sc['title']}",
            "",
            f"- Formula: `{formula.expression}` ({formula.name_en})",
            "- Inputs:",
        ]
        for var, (value, unit) in sc["variables"].items():
            md_lines.append(f"  - `{var}` = {value} {unit}")
        md_lines += [
            f"- **Result**: {readable}",
            f"- Engineering note: {interp}",
            "",
        ]

    audit = out_dir / "mold_calc.md"
    audit.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"\nWrote audit: {audit}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
