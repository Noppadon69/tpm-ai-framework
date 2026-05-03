"""
tpm_progress.data - collect a week's worth of activity for slide gen
ref: MASTER_PLAN_v5.md § 16.4

Sources:
    - .tpm_context/decision_log/daily/<date>/*.json   -> sessions
    - .tpm_context/night_cycle/morning_brief/*.md     -> overnight findings
    - .tpm_context/local_tools/installed/MANIFEST.yaml -> tools added
    - output/{reports,excel}/                          -> artifacts produced
    - git log --since=...                              -> commits this week
"""
from __future__ import annotations

import logging
import subprocess
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from tpm_night.budget_audit import audit_runtime
from tpm_night.session_store import LOG_ROOT, SessionRecord, list_sessions

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
BRIEF_DIR = REPO_ROOT / ".tpm_context" / "night_cycle" / "morning_brief"
MANIFEST_PATH = REPO_ROOT / ".tpm_context" / "local_tools" / "installed" / "MANIFEST.yaml"
OUTPUT_DIRS = [
    REPO_ROOT / "output" / "reports",
    REPO_ROOT / "output" / "excel",
    REPO_ROOT / "output" / "pptx",
    REPO_ROOT / "output" / "progress_reports",
]


# ============================================================
# Data model
# ============================================================
@dataclass
class WeekData:
    week_start: str                                # "YYYY-MM-DD"
    week_end: str                                  # inclusive
    n_days_with_activity: int = 0
    sessions: list[SessionRecord] = field(default_factory=list)
    n_sessions: int = 0
    n_done: int = 0
    n_failed: int = 0
    n_egress_blocks: int = 0
    avg_duration_ms: int = 0
    p90_duration_ms: int = 0
    by_action: dict[str, int] = field(default_factory=dict)
    by_provider: dict[str, int] = field(default_factory=dict)
    by_worker: dict[str, int] = field(default_factory=dict)
    top_tasks: list[dict[str, Any]] = field(default_factory=list)
    auditor_findings: list[str] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    git_commits: list[str] = field(default_factory=list)
    tools_added: list[dict[str, Any]] = field(default_factory=list)
    night_briefs: list[str] = field(default_factory=list)
    repeated_failures: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "week_start": self.week_start,
            "week_end": self.week_end,
            "n_sessions": self.n_sessions,
            "n_done": self.n_done,
            "n_failed": self.n_failed,
            "n_egress_blocks": self.n_egress_blocks,
            "avg_duration_ms": self.avg_duration_ms,
            "p90_duration_ms": self.p90_duration_ms,
            "by_action": self.by_action,
            "by_provider": self.by_provider,
            "by_worker": self.by_worker,
            "top_tasks_count": len(self.top_tasks),
            "artifacts_count": len(self.artifacts),
            "git_commits_count": len(self.git_commits),
        }


# ============================================================
# Helpers
# ============================================================
def _parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def _date_range(start: datetime, end: datetime) -> list[str]:
    days = []
    cur = start
    while cur.date() <= end.date():
        days.append(cur.strftime("%Y-%m-%d"))
        cur += timedelta(days=1)
    return days


# ============================================================
# Collectors
# ============================================================
def _collect_sessions(date_strs: list[str]) -> list[SessionRecord]:
    out: list[SessionRecord] = []
    for d in date_strs:
        out.extend(list_sessions(date=d, limit=500))
    return out


def _collect_artifacts(week_start: datetime) -> list[dict[str, Any]]:
    """Files produced this week from output/ folders."""
    out = []
    cutoff = week_start.timestamp()
    for d in OUTPUT_DIRS:
        if not d.exists():
            continue
        for fp in d.glob("*"):
            if fp.is_file() and fp.suffix in (".docx", ".xlsx", ".pptx", ".pdf", ".md"):
                if fp.stat().st_mtime >= cutoff:
                    out.append({
                        "path": str(fp.relative_to(REPO_ROOT)),
                        "name": fp.name,
                        "kind": fp.suffix.lstrip("."),
                        "size_kb": round(fp.stat().st_size / 1024, 1),
                        "mtime": datetime.fromtimestamp(
                            fp.stat().st_mtime, tz=timezone.utc
                        ).strftime("%Y-%m-%d %H:%M"),
                    })
    return sorted(out, key=lambda x: x["mtime"], reverse=True)


def _collect_git_commits(week_start: datetime) -> list[str]:
    """One-line commit subjects from this week."""
    since = week_start.strftime("%Y-%m-%d")
    out: list[str] = []
    for repo in (REPO_ROOT, REPO_ROOT / ".tpm_context"):
        if not (repo / ".git").exists():
            continue
        try:
            res = subprocess.run(
                ["git", "log", f"--since={since}", "--pretty=format:%h %s"],
                cwd=repo, capture_output=True, text=True, timeout=10,
            )
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    if line.strip():
                        prefix = "[knowl]" if ".tpm_context" in str(repo) else "[fwk] "
                        out.append(f"{prefix} {line}")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            log.warning("git log failed for %s: %s", repo, e)
    return out


def _collect_briefs(date_strs: list[str]) -> list[str]:
    """Names of morning briefs produced this week."""
    out = []
    for d in date_strs:
        path = BRIEF_DIR / f"{d}.md"
        if path.exists():
            out.append(d)
    return out


def _collect_tools(week_start: datetime) -> list[dict[str, Any]]:
    """Read MANIFEST.yaml + return entries installed this week."""
    if not MANIFEST_PATH.exists():
        return []
    try:
        import yaml
        data = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return []
    deps = data.get("dependencies", []) or []
    cutoff = week_start.isoformat()
    return [d for d in deps if isinstance(d, dict) and d.get("installed_at", "") >= cutoff]


def _detect_repeated_failures(sessions: list[SessionRecord]) -> list[str]:
    failed = [s for s in sessions if s.final_phase == "failed"]
    counter: Counter[str] = Counter()
    for s in failed:
        counter[(s.user_request or "")[:40].lower().strip()] += 1
    return [f"{k!r} ({v} times)" for k, v in counter.most_common(3) if v >= 2]


# ============================================================
# Top-level
# ============================================================
def collect_week_data(
    week_end: str | None = None,
    days: int = 7,
) -> WeekData:
    """Gather everything we know about the past N days."""
    end_dt = (
        _parse_date(week_end) if week_end
        else datetime.now(timezone.utc)
    )
    start_dt = end_dt - timedelta(days=days - 1)
    date_strs = _date_range(start_dt, end_dt)

    week = WeekData(
        week_start=start_dt.strftime("%Y-%m-%d"),
        week_end=end_dt.strftime("%Y-%m-%d"),
    )

    sessions = _collect_sessions(date_strs)
    week.sessions = sessions
    week.n_sessions = len(sessions)
    week.n_days_with_activity = len({s.saved_at.strftime("%Y-%m-%d") for s in sessions})

    if sessions:
        stats = audit_runtime(sessions)
        week.n_done = stats.n_done
        week.n_failed = stats.n_failed
        week.n_egress_blocks = stats.egress_blocks
        week.avg_duration_ms = stats.avg()
        week.p90_duration_ms = stats.p90()
        week.auditor_findings = stats.auditor_findings[:20]

        # Group by action / provider / worker
        for s in sessions:
            action = (s.intent or {}).get("action", "?")
            week.by_action[action] = week.by_action.get(action, 0) + 1
            search = (s.final_output or {}).get("search", {})
            if search:
                provider = search.get("provider", "?")
                week.by_provider[provider] = week.by_provider.get(provider, 0) + 1
            worker = (s.final_output or {}).get("worker")
            if worker:
                week.by_worker[worker] = week.by_worker.get(worker, 0) + 1

        # Top tasks - longest 3 by duration_ms
        top = sorted(sessions, key=lambda s: s.duration_ms, reverse=True)[:3]
        for s in top:
            week.top_tasks.append({
                "session_id": s.session_id,
                "user_request": (s.user_request or "")[:80],
                "phase": s.final_phase,
                "duration_s": round(s.duration_ms / 1000, 1) if s.duration_ms else 0,
                "action": (s.intent or {}).get("action", "?"),
                "subject": (s.intent or {}).get("subject", "")[:40],
            })

        week.repeated_failures = _detect_repeated_failures(sessions)

    week.artifacts = _collect_artifacts(start_dt)
    week.git_commits = _collect_git_commits(start_dt)
    week.tools_added = _collect_tools(start_dt)
    week.night_briefs = _collect_briefs(date_strs)
    return week
