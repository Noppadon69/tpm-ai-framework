"""
tpm_mold.defect_catalog - defect -> probable-cause lookup (Section 25.2.2)

Curated from MASTER_PLAN_v6 § 25.2.2. Used by MoldAnalyseNode (§ 25.5) when
diagnosing a defect: returns ranked causes the engineer should check first.

Each cause is annotated with:
  category   - process | tool_wear | material | design
  priority   - 1 (check first) .. 3 (least likely)
  check_via  - which process_param / measurement reveals it
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class InjectionDefect(str, Enum):
    FLASH = "flash"
    SINK_MARK = "sink_mark"
    SHORT_SHOT = "short_shot"
    WARPAGE = "warpage"
    BURN_MARK = "burn_mark"
    WELD_LINE = "weld_line"


class PressDefect(str, Enum):
    BURR = "burr"
    SPRINGBACK = "springback"
    CRACK = "crack"
    WRINKLE = "wrinkle"
    GALLING = "galling"


@dataclass(frozen=True)
class Cause:
    description: str
    category: str           # process | tool_wear | material | design
    priority: int           # 1 highest
    check_via: str          # which param/measurement to look at


DEFECT_CATALOG: dict[str, tuple[Cause, ...]] = {
    InjectionDefect.FLASH.value: (
        Cause("Clamping force too low", "process", 1, "F_clamp vs projected_area"),
        Cause("Parting surface worn / damaged", "tool_wear", 2, "visual mold inspection"),
        Cause("Injection pressure too high", "process", 2, "injection_pressure setting"),
        Cause("Mold deflection under load", "design", 3, "mold structural FEA"),
    ),
    InjectionDefect.SINK_MARK.value: (
        Cause("Holding pressure too low", "process", 1, "holding_pressure"),
        Cause("Holding time too short", "process", 1, "holding_time"),
        Cause("Gate too small / freezes early", "design", 2, "gate cross-section"),
        Cause("Wall section too thick", "design", 2, "part wall thickness"),
        Cause("Melt temperature too low", "process", 3, "barrel_temperature"),
    ),
    InjectionDefect.SHORT_SHOT.value: (
        Cause("Barrel temperature too low", "process", 1, "barrel_temperature"),
        Cause("Injection pressure too low", "process", 1, "injection_pressure"),
        Cause("Vent blockage", "tool_wear", 2, "vent visual inspection"),
        Cause("Insufficient material in barrel", "process", 2, "shot_volume"),
    ),
    InjectionDefect.WARPAGE.value: (
        Cause("Uneven cooling channel flow", "design", 1, "cooling channel layout"),
        Cause("Ejection non-uniform", "tool_wear", 2, "ejector pin condition"),
        Cause("Mold temperature uneven", "process", 2, "mold_temperature"),
        Cause("Internal stress (cooling too fast)", "process", 3, "cooling_time"),
    ),
    InjectionDefect.BURN_MARK.value: (
        Cause("Gas trapped (vent inadequate)", "design", 1, "vent count + size"),
        Cause("Barrel temperature too high", "process", 2, "barrel_temperature"),
        Cause("Injection speed too high", "process", 2, "injection_speed"),
    ),
    InjectionDefect.WELD_LINE.value: (
        Cause("Two melt fronts meeting (multi-gate design)", "design", 1, "gate locations"),
        Cause("Melt temperature too low at meeting point", "process", 2, "barrel_temperature"),
        Cause("Hold pressure insufficient", "process", 2, "holding_pressure"),
    ),
    # Press die
    PressDefect.BURR.value: (
        Cause("Clearance too large", "design", 1, "punch/die clearance"),
        Cause("Punch/die edge worn", "tool_wear", 1, "edge sharpness"),
        Cause("Material too hard for clearance", "material", 3, "material spec"),
    ),
    PressDefect.SPRINGBACK.value: (
        Cause("Overbend angle not compensated", "design", 1, "bend angle setting"),
        Cause("Material yield strength higher than spec", "material", 2, "material cert"),
        Cause("Punch radius too large", "design", 2, "punch R"),
    ),
    PressDefect.CRACK.value: (
        Cause("Bend radius too small", "design", 1, "punch R vs material thickness"),
        Cause("Press force too high", "process", 2, "tonnage"),
        Cause("Material ductility too low", "material", 2, "material elongation"),
    ),
    PressDefect.WRINKLE.value: (
        Cause("Blank holder force too low", "process", 1, "blank holder pressure"),
        Cause("Draw depth too deep for blank", "design", 2, "blank size"),
        Cause("Lubrication insufficient", "process", 3, "lubricant coverage"),
    ),
    PressDefect.GALLING.value: (
        Cause("Lubrication insufficient", "process", 1, "lubricant coverage"),
        Cause("Punch/die surface roughened", "tool_wear", 1, "surface inspection"),
        Cause("Clearance too tight", "design", 2, "punch/die clearance"),
    ),
}


def causes_for(defect: str | InjectionDefect | PressDefect) -> Optional[tuple[Cause, ...]]:
    """
    Lookup ranked causes for a defect (case-insensitive, accepts Thai or
    English keyword). Returns None if unknown.
    """
    if isinstance(defect, (InjectionDefect, PressDefect)):
        return DEFECT_CATALOG.get(defect.value)

    key = defect.lower().strip().replace(" ", "_").replace("-", "_")
    # Direct hit
    if key in DEFECT_CATALOG:
        return DEFECT_CATALOG[key]
    # Common Thai / variant spellings
    aliases = {
        "ขอบคม": "burr",
        "burr_edge": "burr",
        "รอยบุ๋ม": "sink_mark",
        "sinkmark": "sink_mark",
        "ฉีดไม่เต็ม": "short_shot",
        "shortshot": "short_shot",
        "พลาสติกล้น": "flash",
        "ชิ้นงานโก่ง": "warpage",
        "warp": "warpage",
        "รอยไหม้": "burn_mark",
        "burnmark": "burn_mark",
        "รอยประสาน": "weld_line",
        "weldline": "weld_line",
        "ชิ้นงานคืนรูป": "springback",
        "spring_back": "springback",
        "วัสดุแตก": "crack",
        "ผิวยับ": "wrinkle",
        "ผิวขูด": "galling",
    }
    canonical = aliases.get(key)
    return DEFECT_CATALOG.get(canonical) if canonical else None
