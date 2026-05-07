"""tpm_activity - manual activity tracking (Tier 2 of MASTER_PLAN_v5 s 14)

Tier 1 (in-AI) is already covered by .tpm_context/decision_log/daily/.
This module handles MANUAL entries written by the user via
scripts/log_activity.py - things they did WITHOUT the AI in the loop
(repairs, meetings, training, manual lookups, etc.).

Storage: .tpm_context/activity_log/outside_ai/<YYYY-MM-DD>.jsonl
         (one JSON object per line, append-only)
"""
from tpm_activity.tracker import (
    ActivityEntry,
    CATEGORIES,
    list_entries,
    log_entry,
    week_summary,
)

__all__ = ["ActivityEntry", "CATEGORIES", "list_entries", "log_entry", "week_summary"]
