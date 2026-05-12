"""
tpm_night.session_store - persist orchestrator sessions to disk
ref: MASTER_PLAN_v5.md § 15.2 (replay needs source of truth)

Each session saved as JSON to:
    .tpm_context/decision_log/daily/<YYYY-MM-DD>/<session_id>.json

Bounded retention: rotate older than 30 days.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_ROOT = REPO_ROOT / ".tpm_context" / "decision_log" / "daily"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SessionRecord(BaseModel):
    """A persisted session - source of truth for replay + audit."""
    session_id: str
    saved_at: datetime = Field(default_factory=_utcnow)
    user_request: str = ""
    final_phase: str = ""              # "done" | "failed" | etc.
    intent: dict[str, Any] = Field(default_factory=dict)
    final_output: dict[str, Any] = Field(default_factory=dict)
    handoff_log: list[dict[str, Any]] = Field(default_factory=list)
    error: str = ""
    model_name: str = ""
    duration_ms: int = 0
    notes: list[str] = Field(default_factory=list)
    # Inquiry-First (Section 8 - added 2026-05-12)
    inquiry_question: Optional[str] = None
    inquiry_answer: Optional[str] = None
    inquiry_route: Optional[str] = None
    inquiry_skip_reason: Optional[str] = None
    inquiry_payload: Optional[str] = None


# ============================================================
# Save / Load
# ============================================================
def _date_dir(when: Optional[datetime] = None) -> Path:
    when = when or _utcnow()
    d = LOG_ROOT / when.strftime("%Y-%m-%d")
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_session(state: Any, *, started_at: Optional[datetime] = None) -> Path:
    """
    Persist a TPMState (or compatible dict) to disk.
    Returns the saved path.
    """
    # Lazy import to avoid cycle
    from tpm_core.state import TPMState

    if isinstance(state, TPMState):
        s = state
    elif isinstance(state, dict):
        s = TPMState(**state)
    else:
        raise TypeError(f"save_session: unsupported type {type(state)}")

    duration_ms = 0
    if started_at:
        duration_ms = int((_utcnow() - started_at.replace(tzinfo=timezone.utc) if started_at.tzinfo is None else _utcnow() - started_at).total_seconds() * 1000)

    rec = SessionRecord(
        session_id=s.session_id,
        user_request=s.user_request,
        final_phase=s.phase.value,
        intent=s.intent.model_dump() if s.intent else {},
        final_output=s.final_output,
        handoff_log=[p.model_dump(mode="json") for p in s.handoff_log],
        error=s.error,
        model_name=s.model_name,
        duration_ms=duration_ms,
        inquiry_question=s.inquiry_question,
        inquiry_answer=s.inquiry_answer,
        inquiry_route=s.inquiry_route,
        inquiry_skip_reason=s.inquiry_skip_reason,
        inquiry_payload=s.inquiry_payload,
    )

    out_dir = _date_dir(s.started_at)
    out_path = out_dir / f"{s.session_id}.json"
    out_path.write_text(
        rec.model_dump_json(indent=2),
        encoding="utf-8",
    )
    log.info("saved session %s -> %s", s.session_id, out_path)
    return out_path


def load_session(session_id: str) -> Optional[SessionRecord]:
    """Find a session by id across all date folders."""
    if not LOG_ROOT.exists():
        return None
    for date_dir in sorted(LOG_ROOT.iterdir(), reverse=True):
        candidate = date_dir / f"{session_id}.json"
        if candidate.exists():
            data = json.loads(candidate.read_text(encoding="utf-8"))
            return SessionRecord(**data)
    return None


def list_sessions(date: Optional[str] = None, limit: int = 100) -> list[SessionRecord]:
    """
    List sessions.
    `date` = "YYYY-MM-DD" or None for today (UTC).
    Returns newest-first.
    """
    target_date = date or _utcnow().strftime("%Y-%m-%d")
    target_dir = LOG_ROOT / target_date
    if not target_dir.exists():
        return []
    out: list[SessionRecord] = []
    for fp in sorted(target_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            out.append(SessionRecord(**data))
        except (json.JSONDecodeError, ValueError) as e:
            log.warning("could not parse %s: %s", fp, e)
        if len(out) >= limit:
            break
    return out


def list_recent_dates(n: int = 30) -> list[str]:
    """Return up to N most-recent date folders that have sessions."""
    if not LOG_ROOT.exists():
        return []
    dates = []
    for d in sorted(LOG_ROOT.iterdir(), reverse=True):
        if d.is_dir() and any(d.glob("*.json")):
            dates.append(d.name)
        if len(dates) >= n:
            break
    return dates
