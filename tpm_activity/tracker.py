"""
tpm_activity.tracker - manual activity log (out-of-AI work)
ref: MASTER_PLAN_v5 s 14.4 (simplified - no Tier 3 OS-level tracking)

Append-only JSONL files at:
    .tpm_context/activity_log/outside_ai/<YYYY-MM-DD>.jsonl

Each entry: ts, duration_min, category, subject, with_ai, notes
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = REPO_ROOT / ".tpm_context" / "activity_log" / "outside_ai"

# Pre-defined categories - keep small and stable so weekly stats stay legible.
# Free-form `notes` carry the detail.
CATEGORIES = (
    "repair",        # hands-on maintenance / part replacement / troubleshoot
    "inspection",    # PM walk-around, visual checks
    "lookup",        # finding info in manuals/standards/web (with or w/o AI)
    "report",        # writing/editing reports manually
    "calc",          # manual calculations (vs. AI calc worker)
    "training",      # learning / reading / courses
    "meeting",       # standup, review, escalation
    "data_entry",    # logging into ERP / forms / spreadsheets manually
    "idle",          # waiting for parts / approval / data
    "other",
)


# ============================================================
# Data model
# ============================================================
@dataclass
class ActivityEntry:
    ts: str                          # ISO 8601 (when LOGGED, not when started)
    duration_min: float              # how long the activity took (minutes)
    category: str
    subject: str = ""                # equipment ID / topic / report name
    with_ai: bool = False            # did the AI assist? (helps split in-vs-out)
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ActivityEntry":
        # Tolerate legacy/extra fields by filtering to known ones.
        known = {"ts", "duration_min", "category", "subject", "with_ai", "notes"}
        return cls(**{k: v for k, v in d.items() if k in known})


# ============================================================
# Write
# ============================================================
def log_entry(entry: ActivityEntry, log_dir: Path = LOG_DIR) -> Path:
    """Append entry to today's JSONL file. Returns the file path written."""
    log_dir.mkdir(parents=True, exist_ok=True)
    today = entry.ts[:10] if entry.ts else datetime.now(timezone.utc).strftime("%Y-%m-%d")
    fpath = log_dir / f"{today}.jsonl"
    with fpath.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry.as_dict(), ensure_ascii=False) + "\n")
    log.info("activity logged: %s %s (%.0f min) -> %s",
             entry.category, entry.subject[:40], entry.duration_min, fpath.name)
    return fpath


# ============================================================
# Read
# ============================================================
def list_entries(
    date_str: str | None = None,
    log_dir: Path = LOG_DIR,
) -> list[ActivityEntry]:
    """Return entries for a single date (UTC YYYY-MM-DD). Default: today."""
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    fpath = log_dir / f"{date_str}.jsonl"
    if not fpath.exists():
        return []
    entries: list[ActivityEntry] = []
    for line in fpath.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(ActivityEntry.from_dict(json.loads(line)))
        except (json.JSONDecodeError, TypeError) as e:
            log.warning("skipped bad activity line in %s: %s", fpath.name, e)
    return entries


def list_entries_range(
    start_date: str,
    end_date: str,
    log_dir: Path = LOG_DIR,
) -> list[ActivityEntry]:
    """Inclusive date range YYYY-MM-DD..YYYY-MM-DD."""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    out: list[ActivityEntry] = []
    cur = start
    while cur <= end:
        out.extend(list_entries(cur.strftime("%Y-%m-%d"), log_dir))
        cur += timedelta(days=1)
    return out


# ============================================================
# Aggregate (used by weekly progress slides + CLI summary)
# ============================================================
@dataclass
class ActivitySummary:
    n_entries: int = 0
    total_min: float = 0.0
    total_with_ai_min: float = 0.0
    total_without_ai_min: float = 0.0
    by_category_min: dict[str, float] = field(default_factory=dict)
    n_days_with_entries: int = 0

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def week_summary(start_date: str, end_date: str,
                 log_dir: Path = LOG_DIR) -> ActivitySummary:
    """Roll up a week of manual entries into headline numbers for slides."""
    entries = list_entries_range(start_date, end_date, log_dir)
    s = ActivitySummary()
    s.n_entries = len(entries)
    seen_days: set[str] = set()
    for e in entries:
        s.total_min += e.duration_min
        if e.with_ai:
            s.total_with_ai_min += e.duration_min
        else:
            s.total_without_ai_min += e.duration_min
        s.by_category_min[e.category] = s.by_category_min.get(e.category, 0.0) + e.duration_min
        if e.ts:
            seen_days.add(e.ts[:10])
    s.n_days_with_entries = len(seen_days)
    return s
