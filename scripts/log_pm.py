#!/usr/bin/env python
"""
scripts/log_pm.py - CLI to log a PM event (Section 25.2.5 mini-project)

Intern's daily input tool. Each invocation appends one event to
.tpm_context/pm_log/<mold_id>.jsonl.

Examples:
    # First time the mold is seen
    python scripts/log_pm.py M-101 register --material P20 --operator alice

    # Routine clean
    python scripts/log_pm.py M-101 clean --shots 12000 --operator alice

    # Repair with a part replaced
    python scripts/log_pm.py M-101 repair --shots 25000 --part "ejector pin" \
        --notes "noticed wear at pin 4"

    # Log a defect observation
    python scripts/log_pm.py M-101 defect --defect-type "sink_mark" \
        --shots 25100 --notes "part 7 corner"

    # Quick status
    python scripts/log_pm.py M-101 --status
    python scripts/log_pm.py --list

ASCII output for Windows CMD.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import os
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

from tpm_mold.pm_log import (  # noqa: E402
    PMAction,
    PMEvent,
    _utcnow_iso,
    append_event,
    list_molds,
    status_for,
)


def main() -> int:
    p = argparse.ArgumentParser(
        description="Log a PM event for a mold (Section 25 mini-project).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("mold_id", nargs="?", help="mold identifier (e.g. M-101)")
    p.add_argument(
        "action", nargs="?", choices=[a.value for a in PMAction],
        help="PM action type",
    )
    p.add_argument("--shots", type=int, help="cumulative shot count AT this event")
    p.add_argument("--operator", default="", help="who did the work")
    p.add_argument("--material", help="mold steel (set on register)")
    p.add_argument("--part", dest="part_replaced", help="for repair action")
    p.add_argument("--defect-type", dest="defect_type", help="for defect action")
    p.add_argument("--duration", type=int, help="how many minutes the work took")
    p.add_argument("--notes", default="", help="free-text notes")
    p.add_argument("--list", action="store_true", help="list known molds")
    p.add_argument("--status", action="store_true", help="show status for the mold_id")

    args = p.parse_args()

    if args.list:
        molds = list_molds()
        if not molds:
            print("(no molds registered yet)")
            return 0
        print("Registered molds:")
        for m in molds:
            st = status_for(m)
            extra = (
                f"  ({st.material or 'unknown material'}, "
                f"{st.cumulative_shots:,} shots, "
                f"{st.n_events} events)"
            ) if st else ""
            print(f"  {m}{extra}")
        return 0

    if not args.mold_id:
        p.error("mold_id required (or pass --list)")

    if args.status:
        st = status_for(args.mold_id)
        if not st:
            print(f"[FAIL] no log for {args.mold_id} - register first")
            return 2
        print(f"Mold:           {st.mold_id}")
        print(f"Material:       {st.material or '(unknown)'}")
        print(f"Events:         {st.n_events}")
        print(f"Cumulative shots: {st.cumulative_shots:,}")
        print(f"Last action:    {st.last_action} at {st.last_timestamp}")
        if st.last_pm_shots is not None:
            print(f"Last PM at:     {st.last_pm_shots:,} shots")
        print(f"Defects logged: {st.defects_logged}")
        print(f"Repairs logged: {st.repairs_logged}")
        return 0

    if not args.action:
        p.error("action required when not using --list or --status")

    # Build + append
    ev = PMEvent(
        mold_id=args.mold_id,
        timestamp=_utcnow_iso(),
        action=args.action,
        operator=args.operator,
        shot_count=args.shots,
        material=args.material,
        part_replaced=args.part_replaced,
        defect_type=args.defect_type,
        duration_min=args.duration,
        notes=args.notes,
    )
    path = append_event(ev)
    print(f"[OK] logged {ev.action} for {ev.mold_id} -> {path.relative_to(REPO)}")
    if ev.shot_count is not None:
        print(f"     cumulative shots = {ev.shot_count:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
