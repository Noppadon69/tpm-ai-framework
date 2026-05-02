"""
tpm_workers.data_loader - load CM/PM/FMEA from raw_data/_dummy/
ref: MASTER_PLAN_v5.md § 11 (Researcher pattern)

Provides a thin abstraction so when real data arrives in raw_data/excel_logs/,
swapping is just a path change.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
DUMMY_ROOT = REPO_ROOT / "raw_data" / "_dummy"
REAL_ROOT = REPO_ROOT / "raw_data" / "excel_logs"


def _find_first(*candidates: Path) -> Optional[Path]:
    for p in candidates:
        if p.exists():
            return p
    return None


# ============================================================
# CM History (corrective maintenance log)
# ============================================================
class CMHistoryLoader:
    def __init__(self, path: Path | None = None):
        self.path = path or _find_first(
            REAL_ROOT / "CM_History.xlsx",
            DUMMY_ROOT / "excel_logs" / "DUMMY_CM_History_2026.xlsx",
        )
        if self.path is None or not self.path.exists():
            log.warning("CM history file not found - returning empty df")
            self.df = pd.DataFrame()
            self.is_dummy = False
            return
        self.df = pd.read_excel(self.path)
        if "Date" in self.df.columns:
            self.df["Date"] = pd.to_datetime(self.df["Date"])
        self.is_dummy = "_dummy" in str(self.path)
        log.info("Loaded %d CM rows from %s (dummy=%s)",
                 len(self.df), self.path.name, self.is_dummy)

    def for_equipment(self, tag: str) -> pd.DataFrame:
        if self.df.empty or "Machine_Tag" not in self.df.columns:
            return pd.DataFrame()
        mask = self.df["Machine_Tag"].astype(str).str.contains(
            tag, case=False, na=False
        )
        return self.df[mask].copy()

    def recent(self, days: int = 90) -> pd.DataFrame:
        if self.df.empty or "Date" not in self.df.columns:
            return self.df
        cutoff = self.df["Date"].max() - timedelta(days=days)
        return self.df[self.df["Date"] >= cutoff].copy()

    def for_equipment_recent(self, tag: str, days: int = 90) -> pd.DataFrame:
        return self.for_equipment(tag).pipe(
            lambda df: df[df["Date"] >= (df["Date"].max() - timedelta(days=days))]
            if not df.empty and "Date" in df.columns else df
        )


# ============================================================
# PM Schedule
# ============================================================
class PMScheduleLoader:
    def __init__(self, path: Path | None = None):
        self.path = path or _find_first(
            REAL_ROOT / "PM_Schedule.xlsx",
            DUMMY_ROOT / "excel_logs" / "DUMMY_PM_Schedule_2026.xlsx",
        )
        if self.path is None or not self.path.exists():
            self.df = pd.DataFrame()
            self.is_dummy = False
            return
        self.df = pd.read_excel(self.path)
        self.is_dummy = "_dummy" in str(self.path)

    def for_equipment(self, tag: str) -> pd.DataFrame:
        if self.df.empty:
            return self.df
        col = "Equipment" if "Equipment" in self.df.columns else "Machine_Tag"
        if col not in self.df.columns:
            return pd.DataFrame()
        mask = self.df[col].astype(str).str.contains(tag, case=False, na=False)
        return self.df[mask].copy()


# ============================================================
# FMEA reference
# ============================================================
class FMEALoader:
    def __init__(self, path: Path | None = None):
        self.path = path or _find_first(
            REAL_ROOT / "FMEA_Reference.xlsx",
            DUMMY_ROOT / "excel_logs" / "DUMMY_FMEA_Reference.xlsx",
        )
        if self.path is None or not self.path.exists():
            self.df = pd.DataFrame()
            self.is_dummy = False
            return
        self.df = pd.read_excel(self.path)
        self.is_dummy = "_dummy" in str(self.path)

    def for_equipment(self, tag: str) -> pd.DataFrame:
        if self.df.empty or "Equipment" not in self.df.columns:
            return pd.DataFrame()
        mask = self.df["Equipment"].astype(str).str.contains(tag, case=False, na=False)
        return self.df[mask].sort_values("RPN", ascending=False).copy()


# ============================================================
# Convenience: list all known equipment tags
# ============================================================
def list_equipment_tags() -> list[str]:
    cm = CMHistoryLoader()
    if cm.df.empty or "Machine_Tag" not in cm.df.columns:
        return []
    return sorted(cm.df["Machine_Tag"].dropna().unique().tolist())


def is_using_dummy_data() -> bool:
    return CMHistoryLoader().is_dummy
