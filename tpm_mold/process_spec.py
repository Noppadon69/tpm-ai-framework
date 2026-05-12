"""
tpm_mold.process_spec - typical process-parameter ranges (Section 25.2.1)

Used by:
  - report worker / MoldAnalyseNode: flag any param outside the spec range
  - auditor (future): cross-check defect causes against the actual logged
    process values

Spec ranges are general typical values. Actual mold programs may differ -
ALWAYS prefer the program sheet that ships with each tool. These specs are
a "first sanity check" only.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ParamSpec:
    name: str
    unit: str
    typical_min: float
    typical_max: float
    family: str                  # injection | press
    notes: str = ""


PROCESS_SPECS: dict[str, ParamSpec] = {
    # Injection mold parameters
    "barrel_temperature": ParamSpec(
        name="barrel_temperature", unit="degC",
        typical_min=180, typical_max=280,
        family="injection",
        notes="PP: ~200-240, ABS: ~220-260, PC: ~280-310",
    ),
    "mold_temperature": ParamSpec(
        name="mold_temperature", unit="degC",
        typical_min=30, typical_max=120,
        family="injection",
        notes="PP/ABS: 40-80, PC: 80-120",
    ),
    "injection_pressure": ParamSpec(
        name="injection_pressure", unit="MPa",
        typical_min=40, typical_max=180,
        family="injection",
    ),
    "holding_pressure": ParamSpec(
        name="holding_pressure", unit="MPa",
        typical_min=30, typical_max=120,
        family="injection",
    ),
    "cooling_time": ParamSpec(
        name="cooling_time", unit="s",
        typical_min=5, typical_max=45,
        family="injection",
        notes="Roughly = (wall_thickness_mm)^2 * 2-3 s",
    ),
    "cycle_time": ParamSpec(
        name="cycle_time", unit="s",
        typical_min=10, typical_max=90,
        family="injection",
    ),
    # Press die parameters
    "tonnage": ParamSpec(
        name="tonnage", unit="ton",
        typical_min=10, typical_max=800,
        family="press",
        notes="Sheet thickness x shear strength x perimeter governs",
    ),
    "stroke": ParamSpec(
        name="stroke", unit="mm",
        typical_min=20, typical_max=500,
        family="press",
    ),
    "feed_rate": ParamSpec(
        name="feed_rate", unit="mm/stroke",
        typical_min=10, typical_max=600,
        family="press",
    ),
    "material_thickness": ParamSpec(
        name="material_thickness", unit="mm",
        typical_min=0.3, typical_max=6,
        family="press",
        notes="washing-machine sheet typically 0.5 - 1.2 mm",
    ),
}


@dataclass
class ParamCheck:
    name: str
    value: float
    spec: ParamSpec
    in_range: bool
    direction: str       # "low" | "high" | "ok"
    delta_pct: float     # how far outside the range (0.0 if in_range)


def check_param(name: str, value: float) -> Optional[ParamCheck]:
    """
    Compare a measured value against its spec range. Returns None if the
    param is unknown.
    """
    spec = PROCESS_SPECS.get(name.strip())
    if not spec:
        return None
    if value < spec.typical_min:
        delta = (spec.typical_min - value) / spec.typical_min
        return ParamCheck(name=name, value=value, spec=spec,
                          in_range=False, direction="low", delta_pct=delta)
    if value > spec.typical_max:
        delta = (value - spec.typical_max) / spec.typical_max
        return ParamCheck(name=name, value=value, spec=spec,
                          in_range=False, direction="high", delta_pct=delta)
    return ParamCheck(name=name, value=value, spec=spec,
                      in_range=True, direction="ok", delta_pct=0.0)
