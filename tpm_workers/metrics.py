"""
tpm_workers.metrics - reliability metrics (MTBF, MTTR, Availability, Pareto)
ref: MASTER_PLAN_v5.md AGENTS.md Rule #2 (Tool > AI - never let AI compute these)

All math is via numpy/pandas. AI never computes numbers.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


# ============================================================
# Core metrics
# ============================================================
def mtbf_hours(events_df: pd.DataFrame, observation_period_days: int) -> dict[str, float]:
    """
    Mean Time Between Failures (in hours).
    MTBF = (observation_period_hours - sum_downtime_hours) / num_failures
    """
    n_failures = len(events_df)
    obs_hours = observation_period_days * 24
    if n_failures == 0:
        return {
            "mtbf_hours": float("inf"),
            "n_failures": 0,
            "obs_hours": obs_hours,
            "note": "no failures in observation window",
        }
    if "Downtime_Minutes" in events_df.columns:
        downtime_hours = events_df["Downtime_Minutes"].sum() / 60
    else:
        downtime_hours = 0.0
    uptime_hours = max(0.0, obs_hours - downtime_hours)
    mtbf = uptime_hours / n_failures if n_failures else float("inf")
    return {
        "mtbf_hours": round(mtbf, 2),
        "n_failures": n_failures,
        "obs_hours": obs_hours,
        "uptime_hours": round(uptime_hours, 2),
        "downtime_hours": round(downtime_hours, 2),
    }


def mttr_minutes(events_df: pd.DataFrame) -> dict[str, float]:
    """Mean Time To Repair (in minutes). Uses MTTR_Minutes if available, else Downtime_Minutes."""
    if events_df.empty:
        return {"mttr_min": 0.0, "n": 0}
    col = "MTTR_Minutes" if "MTTR_Minutes" in events_df.columns else "Downtime_Minutes"
    if col not in events_df.columns:
        return {"mttr_min": 0.0, "n": len(events_df), "note": "no time column"}
    arr = events_df[col].dropna()
    if arr.empty:
        return {"mttr_min": 0.0, "n": 0}
    return {
        "mttr_min": round(float(arr.mean()), 1),
        "mttr_p50": round(float(arr.median()), 1),
        "mttr_p90": round(float(arr.quantile(0.90)), 1),
        "mttr_max": round(float(arr.max()), 1),
        "n": len(arr),
    }


def availability_pct(events_df: pd.DataFrame, observation_period_days: int) -> float:
    """Availability % = uptime / (uptime + downtime) * 100."""
    if events_df.empty or "Downtime_Minutes" not in events_df.columns:
        return 100.0
    obs_min = observation_period_days * 24 * 60
    downtime_min = events_df["Downtime_Minutes"].sum()
    if obs_min <= 0:
        return 0.0
    return round((obs_min - downtime_min) / obs_min * 100, 2)


# ============================================================
# Pareto analysis (top failure modes)
# ============================================================
def pareto_failures(
    events_df: pd.DataFrame,
    by: str = "Problem_Reported",
    top_n: int = 10,
) -> pd.DataFrame:
    """80/20 ranking by frequency."""
    if events_df.empty or by not in events_df.columns:
        return pd.DataFrame(columns=[by, "count", "pct", "cum_pct"])
    counts = events_df[by].value_counts()
    df = counts.reset_index()
    df.columns = [by, "count"]
    total = df["count"].sum()
    df["pct"] = (df["count"] / total * 100).round(2)
    df["cum_pct"] = df["pct"].cumsum().round(2)
    return df.head(top_n)


# ============================================================
# Cost summary
# ============================================================
def cost_summary(events_df: pd.DataFrame) -> dict[str, float]:
    if events_df.empty:
        return {"total_cost_thb": 0.0, "n": 0}
    cols = [c for c in ("Labor_Cost_THB", "Parts_Cost_THB", "Total_Cost_THB")
            if c in events_df.columns]
    out: dict[str, Any] = {"n": len(events_df)}
    for c in cols:
        out[c.lower()] = round(float(events_df[c].sum()), 2)
    if "Total_Cost_THB" in events_df.columns:
        out["avg_cost_per_event_thb"] = round(
            float(events_df["Total_Cost_THB"].mean()), 2
        )
    return out


# ============================================================
# Severity breakdown
# ============================================================
def severity_breakdown(events_df: pd.DataFrame) -> dict[str, int]:
    if events_df.empty or "Severity" not in events_df.columns:
        return {}
    return events_df["Severity"].value_counts().to_dict()


# ============================================================
# Top-level summary (one shot for all common metrics)
# ============================================================
def full_summary(
    events_df: pd.DataFrame,
    observation_period_days: int = 90,
) -> dict[str, Any]:
    return {
        "n_events": len(events_df),
        "observation_period_days": observation_period_days,
        "mtbf": mtbf_hours(events_df, observation_period_days),
        "mttr": mttr_minutes(events_df),
        "availability_pct": availability_pct(events_df, observation_period_days),
        "cost": cost_summary(events_df),
        "severity": severity_breakdown(events_df),
        "top_5_failures": pareto_failures(events_df, top_n=5).to_dict("records"),
    }
