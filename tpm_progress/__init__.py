"""
tpm_progress - weekly progress report generator
ref: MASTER_PLAN_v5.md § 16.4

Public:
    from tpm_progress import collect_week_data, generate_slides
"""
from tpm_progress.data import WeekData, collect_week_data
from tpm_progress.slides import generate_slides

__all__ = ["WeekData", "collect_week_data", "generate_slides"]

__version__ = "0.1.0"
