"""
log_activity.py - log a manual (out-of-AI) activity entry
ref: MASTER_PLAN_v5 s 14.4 (Tier 2 Workspace Activity)

Usage:
    .venv/Scripts/python.exe scripts/log_activity.py \
        --duration 30 --category repair \
        --subject "MAKINO-a51nx bearing 6205" --notes "replaced left side"

    .venv/Scripts/python.exe scripts/log_activity.py --interactive

    .venv/Scripts/python.exe scripts/log_activity.py --today      # show today's entries
    .venv/Scripts/python.exe scripts/log_activity.py --week       # this-week summary
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# UTF-8 stdout (Windows cp1252 trips on Thai)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from tpm_activity import ActivityEntry, CATEGORIES, list_entries, log_entry, week_summary  # noqa: E402


def _interactive() -> ActivityEntry:
    print("Activity log - interactive mode")
    print(f"  Categories: {', '.join(CATEGORIES)}")
    cat = input("category: ").strip().lower() or "other"
    if cat not in CATEGORIES:
        print(f"  (warning: '{cat}' not in known list - logging anyway)")
    subject = input("subject (equipment / topic): ").strip()
    duration = float(input("duration (minutes): ").strip() or "0")
    with_ai_raw = input("with AI assist? [y/N]: ").strip().lower()
    with_ai = with_ai_raw in ("y", "yes", "ใช่")
    notes = input("notes (optional): ").strip()
    return ActivityEntry(
        ts=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        duration_min=duration,
        category=cat,
        subject=subject,
        with_ai=with_ai,
        notes=notes,
    )


def _show_today() -> int:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    entries = list_entries(today)
    if not entries:
        print(f"No entries logged for {today}.")
        return 0
    print(f"Activity log for {today}  ({len(entries)} entries)")
    print("-" * 64)
    total = 0.0
    for e in entries:
        ai = "[AI]" if e.with_ai else "    "
        subj = (e.subject[:34] + "...") if len(e.subject) > 36 else e.subject
        print(f"  {e.ts[11:16]} {ai} {e.category:11s} {e.duration_min:5.0f}m  {subj}")
        if e.notes:
            print(f"            {e.notes[:60]}")
        total += e.duration_min
    print("-" * 64)
    print(f"  Total: {total:.0f} min ({total/60:.1f} h)")
    return 0


def _show_week() -> int:
    """Roll up the last 7 days (today inclusive)."""
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=6)
    s = week_summary(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
    print(f"Activity summary  {start} .. {end}")
    print("-" * 64)
    print(f"  entries        : {s.n_entries}")
    print(f"  active days    : {s.n_days_with_entries} / 7")
    print(f"  total time     : {s.total_min:.0f} min ({s.total_min/60:.1f} h)")
    print(f"   - with AI     : {s.total_with_ai_min:.0f} min ({s.total_with_ai_min/60:.1f} h)")
    print(f"   - without AI  : {s.total_without_ai_min:.0f} min ({s.total_without_ai_min/60:.1f} h)")
    if s.by_category_min:
        print("  by category    :")
        for cat, mins in sorted(s.by_category_min.items(), key=lambda kv: -kv[1]):
            print(f"     {cat:12s} {mins:5.0f}m  ({mins/60:.1f}h)")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        description="Manual activity logger (Tier 2 of activity tracking)",
    )
    p.add_argument("--duration", type=float, help="duration in minutes")
    p.add_argument("--category", choices=CATEGORIES,
                   help=f"one of: {', '.join(CATEGORIES)}")
    p.add_argument("--subject", default="", help="equipment ID / topic")
    p.add_argument("--notes", default="", help="optional free-form notes")
    p.add_argument("--with-ai", action="store_true",
                   help="mark this activity as AI-assisted")
    p.add_argument("--ts", default=None,
                   help="custom timestamp ISO 8601 (default: now UTC)")
    p.add_argument("--interactive", "-i", action="store_true",
                   help="prompt for fields one by one")
    p.add_argument("--today", action="store_true",
                   help="show today's entries instead of logging")
    p.add_argument("--week", action="store_true",
                   help="show this-week (last 7 days) summary instead of logging")
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    if args.today:
        return _show_today()
    if args.week:
        return _show_week()

    if args.interactive:
        entry = _interactive()
    else:
        if args.duration is None or args.category is None:
            p.error("either --interactive, or both --duration and --category required")
            return 2
        entry = ActivityEntry(
            ts=args.ts or datetime.now(timezone.utc).isoformat(timespec="seconds"),
            duration_min=args.duration,
            category=args.category,
            subject=args.subject,
            with_ai=args.with_ai,
            notes=args.notes,
        )

    log_entry(entry)
    print(f"[ok] logged: {entry.category} {entry.subject!r} ({entry.duration_min:.0f} min)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
