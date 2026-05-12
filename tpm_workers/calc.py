"""
tpm_workers.calc - Calc Worker (Section 11.E, Hard Rule #2: Tool > AI)

Engineering math via SymPy + Pint. NO LLM-generated numbers.

Pipeline:
    1. Pick formula  - keyword match against FORMULA_LIBRARY; fall back to a
                       user-supplied expression in WorkerInput.extras["formula"]
    2. Extract vars  - regex parse "var=number unit" from the user request
    3. Calculate     - SymPy substitution + Pint dimensional check
    4. Format        - human-readable result with formula, inputs, output

Curated library covers Mold & Die + general engineering (Section 25):
    stress, pressure, clamping_force, shot_weight, ohms_law, power,
    pareto_principle (80/20), ratio, strain.

For unknown problems, the user can pass extras={"formula": "F/A",
"values": {"F": 1000, "A": 0.05}} - the worker treats it as ad-hoc.

Public:
    run_calc_worker(WorkerInput) -> WorkerResult
    pick_formula(text, intent) -> formula_id | None
    extract_variables(text) -> dict[str, (value, unit|None)]
    FORMULA_LIBRARY
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import sympy
from pint import UnitRegistry

from tpm_workers.base import WorkerInput, WorkerResult, WorkerStep, WorkerType

log = logging.getLogger(__name__)

_ureg = UnitRegistry()
Q_ = _ureg.Quantity


# ============================================================
# Formula library
# ============================================================
@dataclass(frozen=True)
class Formula:
    id: str
    name_th: str
    name_en: str
    expression: str                       # SymPy-parseable
    variables: tuple[str, ...]            # input symbols required
    output_symbol: str
    output_unit: str                      # Pint-parseable unit string
    description: str
    keywords_th: tuple[str, ...]
    keywords_en: tuple[str, ...]
    # Optional: explicit input units per variable - used for dim check
    var_units: dict[str, str] = None      # type: ignore[assignment]


# Frozen=True forbids defaults of mutable types; use post-init helper.
def _f(**kw) -> Formula:
    kw.setdefault("var_units", {})
    return Formula(**kw)


FORMULA_LIBRARY: dict[str, Formula] = {
    "stress": _f(
        id="stress",
        name_th="ความเค้น",
        name_en="Stress",
        expression="F / A",
        variables=("F", "A"),
        output_symbol="sigma",
        output_unit="pascal",
        description="Normal stress = Force / cross-sectional Area",
        keywords_th=("ความเค้น", "stress", "ซิกม่า"),
        keywords_en=("stress", "sigma", "normal stress"),
        var_units={"F": "newton", "A": "meter**2"},
    ),
    "pressure": _f(
        id="pressure",
        name_th="ความดัน",
        name_en="Pressure",
        expression="F / A",
        variables=("F", "A"),
        output_symbol="P",
        output_unit="pascal",
        description="Pressure = Force / Area",
        keywords_th=("ความดัน", "แรงดัน"),
        keywords_en=("pressure",),
        var_units={"F": "newton", "A": "meter**2"},
    ),
    "clamping_force": _f(
        id="clamping_force",
        name_th="แรงล็อกแม่พิมพ์",
        name_en="Clamping Force (Injection Mold)",
        expression="P * A",
        variables=("P", "A"),
        output_symbol="F_clamp",
        output_unit="newton",
        description="Clamp force = Injection pressure x Projected area (Mold)",
        keywords_th=("แรงล็อก", "clamping", "แม่พิมพ์ฉีด"),
        keywords_en=("clamping force", "clamp force", "injection clamp"),
        var_units={"P": "pascal", "A": "meter**2"},
    ),
    "shot_weight": _f(
        id="shot_weight",
        name_th="น้ำหนัก shot",
        name_en="Shot Weight",
        expression="rho * V",
        variables=("rho", "V"),
        output_symbol="m",
        output_unit="kilogram",
        description="Shot mass = Density x Volume (injection)",
        keywords_th=("น้ำหนัก shot", "shot weight", "มวล shot"),
        keywords_en=("shot weight", "shot mass"),
        var_units={"rho": "kilogram/meter**3", "V": "meter**3"},
    ),
    "ohms_law": _f(
        id="ohms_law",
        name_th="กฎโอห์ม",
        name_en="Ohm's Law",
        expression="I * R",
        variables=("I", "R"),
        output_symbol="V",
        output_unit="volt",
        description="V = I * R",
        keywords_th=("กฎโอห์ม", "โอห์ม"),
        keywords_en=("ohm", "ohm's law", "ohms law"),
        var_units={"I": "ampere", "R": "ohm"},
    ),
    "power_dc": _f(
        id="power_dc",
        name_th="กำลังไฟฟ้า DC",
        name_en="Electrical Power (DC)",
        expression="V * I",
        variables=("V", "I"),
        output_symbol="P",
        output_unit="watt",
        description="DC power = Voltage x Current",
        keywords_th=("กำลังไฟ", "กำลังไฟฟ้า"),
        keywords_en=("electrical power", "power"),
        var_units={"V": "volt", "I": "ampere"},
    ),
    "strain": _f(
        id="strain",
        name_th="ความเครียด",
        name_en="Strain",
        expression="dL / L",
        variables=("dL", "L"),
        output_symbol="epsilon",
        output_unit="dimensionless",
        description="Engineering strain = Change in length / Original length",
        keywords_th=("ความเครียด", "strain", "เอปไซลอน"),
        keywords_en=("strain", "epsilon"),
        var_units={"dL": "meter", "L": "meter"},
    ),
    "ratio": _f(
        id="ratio",
        name_th="อัตราส่วน",
        name_en="Ratio",
        expression="a / b",
        variables=("a", "b"),
        output_symbol="r",
        output_unit="dimensionless",
        description="Generic ratio a / b",
        keywords_th=("อัตราส่วน", "อัตรา"),
        keywords_en=("ratio",),
    ),
    # ---- Mold & Die (Section 25) ----
    "cooling_time_thumb": _f(
        id="cooling_time_thumb",
        name_th="เวลาเย็นตัว (rule of thumb)",
        name_en="Cooling Time (rule of thumb)",
        expression="2 * t**2",   # t in mm -> seconds, factor 2-3 typical
        variables=("t",),
        output_symbol="t_cool",
        output_unit="second",
        description="Approx cooling time = 2 * (wall thickness mm)^2 (s)",
        keywords_th=("เวลาเย็น", "cooling time", "เย็นตัว"),
        keywords_en=("cooling time",),
        var_units={"t": "millimeter"},
    ),
    "projected_area_clamp": _f(
        id="projected_area_clamp",
        name_th="พื้นที่ฉาย (สำหรับแรงล็อก)",
        name_en="Required Projected Area for Clamp Force",
        expression="F / P",
        variables=("F", "P"),
        output_symbol="A_proj",
        output_unit="meter**2",
        description="Projected area needed = clamp force / cavity pressure",
        keywords_th=("พื้นที่ฉาย", "projected area"),
        keywords_en=("projected area",),
        var_units={"F": "newton", "P": "pascal"},
    ),
}


# ============================================================
# Formula picker
# ============================================================
def pick_formula(text: str, intent: dict[str, Any] | None = None) -> Optional[str]:
    """
    Return the formula id whose keyword set best matches the request text.
    None if nothing matches.
    """
    haystack = text.lower()
    if intent:
        haystack += " " + str(intent.get("subject", "")).lower()
        haystack += " " + str(intent.get("scope", "")).lower()

    best: tuple[int, Optional[str]] = (0, None)
    for fid, f in FORMULA_LIBRARY.items():
        score = 0
        for kw in f.keywords_th:
            if kw.lower() in haystack:
                score += 2
        for kw in f.keywords_en:
            if kw.lower() in haystack:
                score += 2
        if score > best[0]:
            best = (score, fid)
    return best[1]


# ============================================================
# Variable extraction
# ============================================================
# Match "F=1000 N", "A = 0.05 m^2", "rho=7850 kg/m^3", "R=10ohm"
# Captures: name / value / unit
_VAR_RE = re.compile(
    r"\b([A-Za-z_][A-Za-z0-9_]{0,15})\s*=\s*"          # name=
    r"([-+]?\d+\.?\d*(?:[eE][-+]?\d+)?)\s*"             # value
    r"([A-Za-z0-9²³µμ°Ω/^()*\-·]*)?"  # optional unit (digits OK for m^3)
)


def extract_variables(text: str) -> dict[str, tuple[float, Optional[str]]]:
    """Pick out 'var = number [unit]' triples from free-text user input."""
    out: dict[str, tuple[float, Optional[str]]] = {}
    for m in _VAR_RE.finditer(text):
        name = m.group(1)
        value = float(m.group(2))
        unit = (m.group(3) or "").strip() or None
        # Normalize common unit notations
        if unit:
            unit = _normalize_unit_token(unit)
        out[name] = (value, unit)
    return out


def _normalize_unit_token(u: str) -> str:
    """Map shorthand symbols to Pint-parseable form."""
    return (
        u.replace("²", "**2")   # squared
         .replace("³", "**3")   # cubed
         .replace("^", "**")    # caret -> python power
         .replace("Ω", "ohm")   # capital omega -> ohm
         .replace("µ", "u")     # micro sign (already kg etc.)
         .replace("μ", "u")
         .replace("·", "*")     # middle dot
    )


# ============================================================
# Calculator
# ============================================================
@dataclass
class CalcResult:
    formula_id: str
    expression: str
    inputs: dict[str, Any]                # {name: pint Quantity or float}
    output_value: float
    output_unit: str
    pretty: str                           # human-readable summary
    missing_vars: list[str] = None        # type: ignore[assignment]
    dim_check_ok: bool = True
    warnings: list[str] = None            # type: ignore[assignment]

    def __post_init__(self):
        if self.missing_vars is None:
            self.missing_vars = []
        if self.warnings is None:
            self.warnings = []


def calculate(
    formula: Formula,
    var_values: dict[str, tuple[float, Optional[str]]],
) -> CalcResult:
    """
    Substitute the user-provided values into the formula and compute.
    Uses Pint for unit conversion to the formula's expected input units.
    """
    # Build explicit Symbol objects for each declared variable. Without this,
    # sympy.sympify("I * R") would treat "I" as the imaginary unit and any
    # numeric substitution then yields a complex number we can't float().
    syms: dict[str, Any] = {v: sympy.Symbol(v) for v in formula.variables}
    expr = sympy.parsing.sympy_parser.parse_expr(
        formula.expression, local_dict=syms
    )

    inputs: dict[str, Any] = {}
    missing: list[str] = []
    warnings: list[str] = []
    sub: dict[Any, Any] = {}

    for var in formula.variables:
        if var not in var_values:
            missing.append(var)
            continue

        value, unit = var_values[var]
        expected = formula.var_units.get(var) if formula.var_units else None

        if unit and expected:
            try:
                q = Q_(value, unit).to(expected)
                inputs[var] = q
                sub_value = float(q.magnitude)
            except Exception as e:  # noqa: BLE001
                warnings.append(
                    f"unit conversion failed for {var}: {unit} -> {expected} ({e})"
                )
                inputs[var] = value
                sub_value = value
        else:
            if expected and not unit:
                warnings.append(
                    f"no unit given for {var} - assuming {expected}"
                )
            inputs[var] = (value if not unit else Q_(value, unit))
            sub_value = value

        if var in syms:
            sub[syms[var]] = sub_value

    if missing:
        return CalcResult(
            formula_id=formula.id,
            expression=formula.expression,
            inputs=inputs,
            output_value=float("nan"),
            output_unit=formula.output_unit,
            pretty=f"missing variables: {missing}",
            missing_vars=missing,
            warnings=warnings,
        )

    result = float(expr.evalf(subs=sub))
    pretty = _format_pretty(formula, inputs, result, warnings)
    return CalcResult(
        formula_id=formula.id,
        expression=formula.expression,
        inputs=inputs,
        output_value=result,
        output_unit=formula.output_unit,
        pretty=pretty,
        warnings=warnings,
    )


def _format_pretty(
    f: Formula,
    inputs: dict[str, Any],
    result: float,
    warnings: list[str],
) -> str:
    lines = [
        f"Formula: {f.name_en} ({f.id})",
        f"  {f.output_symbol} = {f.expression}",
        f"  ({f.description})",
        "",
        "Inputs:",
    ]
    for var in f.variables:
        v = inputs.get(var)
        if hasattr(v, "magnitude"):
            lines.append(f"  {var} = {v.magnitude:g} {v.units:~P}")
        else:
            lines.append(f"  {var} = {v}")
    lines.append("")
    # Try to format result with unit
    try:
        q = Q_(result, f.output_unit)
        # Compact: 50000 Pa -> 50 kPa where natural
        compact = q.to_compact() if f.output_unit != "dimensionless" else q
        lines.append(f"Result: {f.output_symbol} = {compact.magnitude:.6g} {compact.units:~P}")
    except Exception:  # noqa: BLE001
        lines.append(f"Result: {f.output_symbol} = {result:.6g} {f.output_unit}")
    if warnings:
        lines.append("")
        lines.append("Warnings:")
        for w in warnings:
            lines.append(f"  - {w}")
    return "\n".join(lines)


# ============================================================
# Worker entry point
# ============================================================
def run_calc_worker(inp: WorkerInput) -> WorkerResult:
    """
    1. Pick formula (by keyword or extras["formula"])
    2. Extract variables from user_request (or extras["values"])
    3. Calculate via SymPy + Pint
    4. Write a small .md audit trail to output_dir
    """
    result = WorkerResult(worker_type=WorkerType.CALC, success=False)

    # ----- Step 1: pick formula -----
    step1 = WorkerStep(name="pick_formula")
    extras = inp.extras or {}
    formula_id = extras.get("formula_id") or pick_formula(inp.user_request, inp.intent)
    ad_hoc_expr = extras.get("formula")  # raw expression like "F/A"

    if formula_id and formula_id in FORMULA_LIBRARY:
        formula = FORMULA_LIBRARY[formula_id]
        step1.notes.append(f"matched library formula: {formula.name_en}")
    elif ad_hoc_expr:
        # Ad-hoc expression - build a transient Formula.
        # Use the user-supplied 'values' dict (if any) as the symbol whitelist
        # so SymPy doesn't reinterpret variable letters like I/E/N as builtins.
        try:
            hint_vars = list((extras.get("values") or {}).keys())
            local_syms = {v: sympy.Symbol(v) for v in hint_vars}
            parsed = sympy.parsing.sympy_parser.parse_expr(
                ad_hoc_expr, local_dict=local_syms
            )
            free = sorted(str(s) for s in parsed.free_symbols)
            formula = Formula(
                id="adhoc",
                name_th="(สูตรเฉพาะ)",
                name_en="(ad-hoc expression)",
                expression=ad_hoc_expr,
                variables=tuple(free),
                output_symbol="result",
                output_unit="dimensionless",
                description=f"ad-hoc: {ad_hoc_expr}",
                keywords_th=(),
                keywords_en=(),
                var_units={},
            )
            step1.notes.append(f"parsed ad-hoc: {ad_hoc_expr} (vars={free})")
        except sympy.SympifyError as e:
            step1.finish(success=False, error=f"cannot parse expression: {e}")
            result.add_step(step1)
            result.summary = f"calc failed: invalid expression {ad_hoc_expr!r}"
            return result
    else:
        step1.finish(success=False, error="no formula matched and no ad-hoc expression")
        result.add_step(step1)
        result.summary = (
            "calc failed: could not match a formula from the library. "
            f"Available: {sorted(FORMULA_LIBRARY)}. Pass extras['formula'] "
            "to provide a custom expression."
        )
        return result
    step1.output = {"formula_id": formula.id, "expression": formula.expression}
    step1.finish(success=True)
    result.add_step(step1)

    # ----- Step 2: extract variables -----
    step2 = WorkerStep(name="extract_variables")
    explicit_values = extras.get("values") or {}
    explicit_units = extras.get("units") or {}
    var_values: dict[str, tuple[float, Optional[str]]] = {}

    if explicit_values:
        for k, v in explicit_values.items():
            var_values[k] = (float(v), explicit_units.get(k))
        step2.notes.append(f"from extras: {list(var_values)}")
    else:
        var_values = extract_variables(inp.user_request)
        step2.notes.append(f"regex-parsed: {list(var_values)}")
    step2.output = {var: {"value": v[0], "unit": v[1]} for var, v in var_values.items()}
    step2.finish(success=bool(var_values))
    result.add_step(step2)

    # ----- Step 3: calculate -----
    step3 = WorkerStep(name="calculate")
    calc = calculate(formula, var_values)
    if calc.missing_vars:
        step3.finish(success=False, error=f"missing vars: {calc.missing_vars}")
        result.summary = (
            f"calc incomplete: missing {calc.missing_vars} for {formula.name_en}. "
            f"Required: {list(formula.variables)}"
        )
        result.add_step(step3)
        result.metrics = {"missing_vars": calc.missing_vars}
        return result
    step3.output = {
        "value": calc.output_value,
        "unit": calc.output_unit,
        "warnings": calc.warnings,
    }
    step3.notes.append(f"= {calc.output_value:.6g} {calc.output_unit}")
    step3.finish(success=True)
    result.add_step(step3)

    # ----- Step 4: write audit trail -----
    step4 = WorkerStep(name="write_audit")
    inp.output_dir.mkdir(parents=True, exist_ok=True)
    audit_path = inp.output_dir / f"calc_{inp.session_id}.md"
    audit_path.write_text(
        f"# Calc audit - {inp.session_id}\n\n"
        f"**Request:** {inp.user_request}\n\n"
        f"```\n{calc.pretty}\n```\n",
        encoding="utf-8",
    )
    step4.output = {"path": str(audit_path)}
    step4.finish(success=True)
    result.add_step(step4)

    # ----- Done -----
    result.success = True
    result.output_files = [str(audit_path)]
    result.summary = (
        f"{formula.name_en}: {formula.output_symbol} = "
        f"{calc.output_value:.6g} {calc.output_unit}"
    )
    result.metrics = {
        "formula_id": formula.id,
        "value": calc.output_value,
        "unit": calc.output_unit,
        "inputs": {k: (v.magnitude if hasattr(v, "magnitude") else v)
                   for k, v in calc.inputs.items()},
        "pretty": calc.pretty,
    }
    result.confidence = 1.0 if not calc.warnings else 0.85

    # Auditor (Section 12 - lightweight pass for calc results)
    try:
        from tpm_workers.auditor import audit_worker_result
        ctx = {
            "claim_text": calc.pretty,
            # source_text = the formula + inputs as a canonical reference
            "source_text": (
                f"{formula.expression} with " +
                ", ".join(f"{k}={v}" for k, v in (extras.get("values") or {}).items())
                + f" -> {calc.output_value}"
            ),
        }
        report = audit_worker_result(result, ctx)
        for v in report.layers:
            if v.findings:
                tag = "" if v.severity == "info" else f" [{v.severity}]"
                for f in v.findings:
                    result.auditor_findings.append(f"{v.layer}{tag}: {f}")
        result.auditor_passed = report.passed
    except Exception as e:  # noqa: BLE001
        log.warning("calc auditor failed: %s", e)

    return result
