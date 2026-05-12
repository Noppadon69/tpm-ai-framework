"""
tpm_mold.materials - mold-material property DB (Section 25.4)

Hardness, yield strength, typical application. Used by:
  - report worker (cite material spec inline)
  - calc worker (default values when user doesn't provide them)
  - audit/safety (flag material/process mismatch)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Material:
    name: str
    family: str                    # tool_steel | structural_steel | plastic
    hardness_hrc: tuple[int, int]   # (min, max) Rockwell C
    yield_strength_mpa: int
    tensile_strength_mpa: int
    density_kg_m3: float
    typical_application: str
    notes: str = ""


MATERIALS: dict[str, Material] = {
    # Tool steels (injection mold)
    "SKD61": Material(
        name="SKD61", family="tool_steel",
        hardness_hrc=(50, 55),
        yield_strength_mpa=1380, tensile_strength_mpa=1620,
        density_kg_m3=7800,
        typical_application="injection mold core/cavity (hot-work, thermal cycling)",
    ),
    "P20": Material(
        name="P20", family="tool_steel",
        hardness_hrc=(28, 36),
        yield_strength_mpa=860, tensile_strength_mpa=1000,
        density_kg_m3=7860,
        typical_application="injection mold base, low-volume cavities",
    ),
    "NAK80": Material(
        name="NAK80", family="tool_steel",
        hardness_hrc=(38, 43),
        yield_strength_mpa=1100, tensile_strength_mpa=1300,
        density_kg_m3=7800,
        typical_application="cosmetic injection mold (mirror finish)",
    ),
    # Tool steels (press die)
    "SKD11": Material(
        name="SKD11", family="tool_steel",
        hardness_hrc=(58, 62),
        yield_strength_mpa=1900, tensile_strength_mpa=2150,
        density_kg_m3=7700,
        typical_application="press die (punch/die for sheet metal, wear-resistant)",
    ),
    # Structural steel
    "S50C": Material(
        name="S50C", family="structural_steel",
        hardness_hrc=(20, 28),
        yield_strength_mpa=380, tensile_strength_mpa=620,
        density_kg_m3=7850,
        typical_application="press die base, low-cost die holders",
    ),
    # Plastics commonly molded for washing-machine parts (Section 25)
    "PP": Material(
        name="PP", family="plastic",
        hardness_hrc=(0, 0),         # not applicable
        yield_strength_mpa=35, tensile_strength_mpa=35,
        density_kg_m3=905,
        typical_application="washing machine tub liner, agitator (PP homo/copo)",
    ),
    "ABS": Material(
        name="ABS", family="plastic",
        hardness_hrc=(0, 0),
        yield_strength_mpa=44, tensile_strength_mpa=44,
        density_kg_m3=1050,
        typical_application="washing machine outer cabinet, control panel housing",
    ),
    "PC": Material(
        name="PC", family="plastic",
        hardness_hrc=(0, 0),
        yield_strength_mpa=62, tensile_strength_mpa=68,
        density_kg_m3=1200,
        typical_application="control panel transparent windows, light covers",
    ),
}


def material_info(name: str) -> Optional[Material]:
    """Case-insensitive lookup."""
    return MATERIALS.get(name.upper().strip())
