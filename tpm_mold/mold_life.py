"""
tpm_mold.mold_life - mold-material life rules (Section 25.2.3)

PM interval and overhaul threshold per mold steel. Drives PM scheduler:
given a shot/stroke counter, decide when to schedule next PM and
when to flag overhaul.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class MoldLifeRule:
    material: str
    family: str               # injection_mold | press_die
    pm_interval: int          # shots (injection) or strokes (press)
    overhaul_threshold: int   # cumulative shots/strokes before major rebuild
    typical_hardness_hrc: tuple[int, int]
    notes: str = ""


LIFE_RULES: dict[str, MoldLifeRule] = {
    # Injection mold steels
    "SKD61": MoldLifeRule(
        material="SKD61", family="injection_mold",
        pm_interval=50_000, overhaul_threshold=500_000,
        typical_hardness_hrc=(50, 55),
        notes="hot-work steel; resists thermal fatigue, common in TPM injection molds",
    ),
    "P20": MoldLifeRule(
        material="P20", family="injection_mold",
        pm_interval=30_000, overhaul_threshold=300_000,
        typical_hardness_hrc=(28, 36),
        notes="pre-hardened steel; easy machining, lower hardness limits life",
    ),
    "NAK80": MoldLifeRule(
        material="NAK80", family="injection_mold",
        pm_interval=20_000, overhaul_threshold=200_000,
        typical_hardness_hrc=(38, 43),
        notes="age-hardenable mirror-finish steel for visual cosmetic parts",
    ),
    # Press die steels
    "SKD11": MoldLifeRule(
        material="SKD11", family="press_die",
        pm_interval=100_000, overhaul_threshold=1_000_000,
        typical_hardness_hrc=(58, 62),
        notes="cold-work tool steel; wear-resistant for press dies",
    ),
    "S50C": MoldLifeRule(
        material="S50C", family="press_die",
        pm_interval=10_000, overhaul_threshold=100_000,
        typical_hardness_hrc=(20, 28),
        notes="medium-carbon steel; budget choice with short life",
    ),
}


def life_rules_for(
    material: str,
    family: Optional[str] = None,
) -> Optional[MoldLifeRule]:
    """Lookup life rule by material name. family filter is optional."""
    rule = LIFE_RULES.get(material.upper().strip())
    if not rule:
        return None
    if family and rule.family != family:
        return None
    return rule


def next_pm_due(rule: MoldLifeRule, cumulative_count: int) -> int:
    """
    Number of shots/strokes remaining until the next PM is due.
    Returns 0 if the current cycle count is exactly at a PM interval.
    Returns negative if PM is overdue (caller should flag).
    """
    if rule.pm_interval <= 0:
        return 0
    remainder = cumulative_count % rule.pm_interval
    if remainder == 0:
        return 0
    return rule.pm_interval - remainder


def is_overhaul_due(rule: MoldLifeRule, cumulative_count: int) -> bool:
    """True when the mold has hit its overhaul threshold."""
    return cumulative_count >= rule.overhaul_threshold
