"""
tpm_mold.pm_log - PM event tracking (Section 25.2.5 mini-project shell)

Data model + JSONL persistence for "what happened to mold X over time".
Used by:
  - scripts/log_pm.py - CLI to add events (intern uses on Day 1)
  - scripts/pm_dashboard.py - matplotlib visualizations
  - Future: feed Report worker / MoldAnalyseNode with mold history

Storage:
  .tpm_context/pm_log/<mold_id>.jsonl    (one line per event, append-only)
  Per-mold file means we never have to lock a shared log.

Designed to work with ZERO real data - the CLI bootstraps each new mold
with a "register" event so Day 1 of the internship is literal drop-in.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
PM_LOG_DIR = REPO_ROOT / ".tpm_context" / "pm_log"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class PMAction(str, Enum):
    REGISTER = "register"       # initial registration (must be first event)
    INSPECT = "inspect"         # routine inspection
    CLEAN = "clean"             # cleaning only
    LUBRICATE = "lubricate"     # lubrication
    REPAIR = "repair"           # repair (specify part_replaced)
    OVERHAUL = "overhaul"       # full overhaul
    SHOT_COUNT = "shot_count"   # just updating cumulative shot count
    DEFECT = "defect"           # defect observed (specify defect_type)
    NOTE = "note"               # free-text note


@dataclass
class PMEvent:
    mold_id: str
    timestamp: str                              # ISO8601 UTC
    action: str                                 # one of PMAction values
    operator: str = ""                          # who did the work
    shot_count: Optional[int] = None            # cumulative count AT this event
    material: Optional[str] = None              # mold steel (set on register)
    part_replaced: Optional[str] = None         # for REPAIR
    defect_type: Optional[str] = None           # for DEFECT
    duration_min: Optional[int] = None          # how long the work took
    notes: str = ""

    def to_jsonl(self) -> str:
        d = {k: v for k, v in asdict(self).items() if v is not None and v != ""}
        return json.dumps(d, ensure_ascii=False)


def _log_path(mold_id: str) -> Path:
    safe = mold_id.replace("/", "_").replace("\\", "_")
    return PM_LOG_DIR / f"{safe}.jsonl"


def append_event(event: PMEvent) -> Path:
    """Append a single event to the mold's JSONL log."""
    PM_LOG_DIR.mkdir(parents=True, exist_ok=True)
    p = _log_path(event.mold_id)
    with p.open("a", encoding="utf-8") as f:
        f.write(event.to_jsonl() + "\n")
    return p


def register_mold(
    mold_id: str,
    material: str,
    operator: str = "",
    notes: str = "",
) -> PMEvent:
    """Convenience: register a new mold (creates JSONL file)."""
    ev = PMEvent(
        mold_id=mold_id,
        timestamp=_utcnow_iso(),
        action=PMAction.REGISTER.value,
        operator=operator,
        material=material,
        shot_count=0,
        notes=notes or "initial registration",
    )
    append_event(ev)
    return ev


def list_molds() -> list[str]:
    """List mold IDs that have a log file."""
    if not PM_LOG_DIR.exists():
        return []
    return sorted(p.stem for p in PM_LOG_DIR.glob("*.jsonl"))


def load_events(mold_id: str) -> list[PMEvent]:
    """Load all events for a mold, oldest first."""
    p = _log_path(mold_id)
    if not p.exists():
        return []
    events: list[PMEvent] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
            events.append(PMEvent(**d))
        except (json.JSONDecodeError, TypeError):
            continue
    return events


# ============================================================
# Derived queries
# ============================================================
@dataclass
class MoldStatus:
    mold_id: str
    material: Optional[str]
    n_events: int
    cumulative_shots: int
    last_action: Optional[str]
    last_timestamp: Optional[str]
    last_pm_shots: Optional[int]
    defects_logged: int
    repairs_logged: int


def status_for(mold_id: str) -> Optional[MoldStatus]:
    """Compute the latest snapshot for one mold."""
    events = load_events(mold_id)
    if not events:
        return None

    material = next((e.material for e in events if e.material), None)
    cumulative_shots = max((e.shot_count or 0) for e in events)
    last = events[-1]
    last_pm_event = next(
        (e for e in reversed(events)
         if e.action in (PMAction.CLEAN.value, PMAction.INSPECT.value,
                         PMAction.LUBRICATE.value, PMAction.REPAIR.value,
                         PMAction.OVERHAUL.value)),
        None,
    )
    return MoldStatus(
        mold_id=mold_id,
        material=material,
        n_events=len(events),
        cumulative_shots=cumulative_shots,
        last_action=last.action,
        last_timestamp=last.timestamp,
        last_pm_shots=last_pm_event.shot_count if last_pm_event else None,
        defects_logged=sum(1 for e in events if e.action == PMAction.DEFECT.value),
        repairs_logged=sum(1 for e in events if e.action == PMAction.REPAIR.value),
    )


def events_in_range(
    mold_id: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> list[PMEvent]:
    """Filter events to a time window. ISO8601 strings, both inclusive."""
    events = load_events(mold_id)
    if start:
        events = [e for e in events if e.timestamp >= start]
    if end:
        events = [e for e in events if e.timestamp <= end]
    return events


def defect_breakdown(mold_id: str) -> dict[str, int]:
    """Count defects by type for one mold."""
    out: dict[str, int] = {}
    for e in load_events(mold_id):
        if e.action == PMAction.DEFECT.value and e.defect_type:
            out[e.defect_type] = out.get(e.defect_type, 0) + 1
    return out


def shots_between_pm(mold_id: str) -> list[int]:
    """
    Return shot-count deltas between consecutive PM events.
    Useful for plotting "did we hit PM intervals?" on the dashboard.
    """
    pm_actions = {
        PMAction.CLEAN.value, PMAction.INSPECT.value,
        PMAction.LUBRICATE.value, PMAction.REPAIR.value, PMAction.OVERHAUL.value,
    }
    pm_shots: list[int] = []
    for e in load_events(mold_id):
        if e.action in pm_actions and e.shot_count is not None:
            pm_shots.append(e.shot_count)
    if len(pm_shots) < 2:
        return []
    return [pm_shots[i + 1] - pm_shots[i] for i in range(len(pm_shots) - 1)]
