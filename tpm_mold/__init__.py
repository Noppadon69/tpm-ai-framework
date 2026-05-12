"""
tpm_mold - Mold & Die domain knowledge (Section 25)

Toshiba internship scope: injection mold + press die for washing-machine parts.

Submodules:
  defect_catalog - defect -> probable causes lookup (Flash, Sink, Burr, ...)
  mold_life      - material -> PM interval + overhaul threshold (shots/strokes)
  materials      - material -> hardness, yield strength, application
  process_spec   - typical process-parameter ranges (injection / press)
"""
from tpm_mold.defect_catalog import (
    DEFECT_CATALOG,
    InjectionDefect,
    PressDefect,
    causes_for,
)
from tpm_mold.materials import MATERIALS, Material, material_info
from tpm_mold.mold_life import MoldLifeRule, life_rules_for
from tpm_mold.process_spec import PROCESS_SPECS, ParamSpec, check_param

__all__ = [
    "DEFECT_CATALOG",
    "InjectionDefect",
    "PressDefect",
    "causes_for",
    "MATERIALS",
    "Material",
    "material_info",
    "MoldLifeRule",
    "life_rules_for",
    "PROCESS_SPECS",
    "ParamSpec",
    "check_param",
]
