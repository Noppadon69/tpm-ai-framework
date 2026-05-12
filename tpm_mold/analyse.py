"""
tpm_mold.analyse - MoldAnalyseNode (Section 25.5)

Deterministic root-cause assembly: given a defect and the process log
that produced it, return a ranked list of candidate causes filtered by
which process params actually deviated from spec.

No LLM call - this is the pre-LLM filter that hands a small, focused
candidate list to the orchestrator. The LLM step (final synthesis) is
done elsewhere; this module's job is to do the cheap, deterministic part
so the LLM only handles the synthesis.

Public:
    MoldDiagnosis dataclass
    analyse(defect, process_log, mold_material=None, shot_count=None) -> MoldDiagnosis
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from tpm_mold.defect_catalog import Cause, causes_for
from tpm_mold.materials import Material, material_info
from tpm_mold.mold_life import MoldLifeRule, is_overhaul_due, life_rules_for, next_pm_due
from tpm_mold.process_spec import ParamCheck, check_param


@dataclass
class ParamDeviation:
    param: str
    value: float
    expected_range: tuple[float, float]
    direction: str
    delta_pct: float

    def short(self) -> str:
        return (
            f"{self.param}={self.value} {self.direction} "
            f"(expected {self.expected_range[0]}..{self.expected_range[1]}, "
            f"{self.delta_pct*100:.0f}% off)"
        )


@dataclass
class MoldDiagnosis:
    defect: str
    causes: list[Cause] = field(default_factory=list)
    deviations: list[ParamDeviation] = field(default_factory=list)
    material_info: Optional[Material] = None
    life_rule: Optional[MoldLifeRule] = None
    pm_due_in: Optional[int] = None
    overhaul_due: bool = False
    ranked_candidates: list[Cause] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        """Compact human-readable summary."""
        lines = [f"Defect: {self.defect}"]
        if not self.causes:
            return f"Defect: {self.defect} (unknown - no catalog entry)"

        if self.deviations:
            lines.append("Param deviations:")
            for d in self.deviations:
                lines.append(f"  - {d.short()}")
        else:
            lines.append("Param deviations: none detected")

        if self.life_rule:
            lines.append(
                f"Mold material: {self.life_rule.material} "
                f"(family={self.life_rule.family}, "
                f"HRC {self.life_rule.typical_hardness_hrc[0]}-{self.life_rule.typical_hardness_hrc[1]})"
            )
            if self.pm_due_in is not None:
                lines.append(f"Next PM in: {self.pm_due_in} shots/strokes")
            if self.overhaul_due:
                lines.append("OVERHAUL DUE - cumulative count past threshold")

        lines.append("")
        lines.append(f"Ranked candidates ({len(self.ranked_candidates)}):")
        for i, c in enumerate(self.ranked_candidates[:5], 1):
            lines.append(
                f"  {i}. [{c.category}, p={c.priority}] {c.description}"
            )
            lines.append(f"     check via: {c.check_via}")

        if self.warnings:
            lines.append("")
            lines.append("Warnings:")
            for w in self.warnings:
                lines.append(f"  - {w}")

        return "\n".join(lines)


def analyse(
    defect: str,
    process_log: Optional[dict[str, float]] = None,
    mold_material: Optional[str] = None,
    shot_count: Optional[int] = None,
) -> MoldDiagnosis:
    """
    Deterministic mold-defect analysis.

    Args:
        defect: Defect name (English, Thai alias, or enum value).
        process_log: Dict of process_param -> measured value. Each key must
                     match a name in tpm_mold.process_spec.PROCESS_SPECS for
                     a deviation check to fire.
        mold_material: Optional mold-steel name (e.g., "SKD61"). Triggers
                       life-rule + PM checks.
        shot_count: Cumulative shot/stroke count - required for PM
                    countdown and overhaul check.

    Returns:
        MoldDiagnosis with causes, deviations, life info, and a ranked
        candidate list (deviation-aware ordering).
    """
    diag = MoldDiagnosis(defect=defect)

    # 1. Catalog lookup
    catalog_causes = causes_for(defect)
    if not catalog_causes:
        diag.warnings.append(
            f"defect {defect!r} not in catalog - check spelling or add to "
            "tpm_mold/defect_catalog.py"
        )
        return diag
    diag.causes = list(catalog_causes)

    # 2. Process-param deviations
    if process_log:
        for name, value in process_log.items():
            chk = check_param(name, value)
            if chk and not chk.in_range:
                diag.deviations.append(ParamDeviation(
                    param=name, value=value,
                    expected_range=(chk.spec.typical_min, chk.spec.typical_max),
                    direction=chk.direction,
                    delta_pct=chk.delta_pct,
                ))
            elif chk is None:
                diag.warnings.append(f"unknown param: {name}")

    # 3. Material + life rule
    if mold_material:
        diag.material_info = material_info(mold_material)
        diag.life_rule = life_rules_for(mold_material)
        if diag.life_rule is None:
            diag.warnings.append(
                f"no life rule for material {mold_material!r}"
            )
        elif shot_count is not None:
            diag.pm_due_in = next_pm_due(diag.life_rule, shot_count)
            diag.overhaul_due = is_overhaul_due(diag.life_rule, shot_count)

    # 4. Rank candidates: causes whose check_via mentions a deviating param
    #    are bumped up; otherwise keep priority order.
    deviating_params = {d.param for d in diag.deviations}
    overhaul_bump = diag.overhaul_due

    def rank_score(c: Cause) -> tuple[int, int]:
        # Lower tuple = better rank
        base = c.priority
        # bump if its check_via mentions a deviating param
        boost = 0
        for p in deviating_params:
            if p in c.check_via:
                boost -= 2
                break
        # If overhaul is due, bump tool_wear causes
        if overhaul_bump and c.category == "tool_wear":
            boost -= 1
        return (base + boost, c.priority)

    diag.ranked_candidates = sorted(diag.causes, key=rank_score)
    return diag
