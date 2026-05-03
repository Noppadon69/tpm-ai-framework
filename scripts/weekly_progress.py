"""
weekly_progress.py - generate weekly progress slides
ref: MASTER_PLAN_v5.md § 16.4

Usage:
    python scripts/weekly_progress.py                  # this week (today - 6d)
    python scripts/weekly_progress.py --end 2026-05-09 # specific week-end
    python scripts/weekly_progress.py --days 14        # last 2 weeks
    python scripts/weekly_progress.py --json           # also dump WeekData JSON

Cron (Linux/WSL):
    0 17 * * 5  cd /path/to/tpm_workspace && .venv/bin/python scripts/weekly_progress.py

Windows Task Scheduler:
    Trigger:  Weekly, Friday 17:00
    Action:   D:\\tpm_workspace\\.venv\\Scripts\\python.exe scripts\\weekly_progress.py
    Start in: D:\\tpm_workspace
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

# UTF-8 stdout (Windows console)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

# Load .env
_env_file = REPO / ".env"
if _env_file.exists():
    for line in _env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from tpm_progress import collect_week_data, generate_slides  # noqa: E402

log = logging.getLogger(__name__)


def main() -> int:
    p = argparse.ArgumentParser(description="TPM AI - weekly progress slides")
    p.add_argument("--end", default=None,
                   help="week-end YYYY-MM-DD (default: today UTC)")
    p.add_argument("--days", type=int, default=7, help="window size (default 7)")
    p.add_argument("--json", action="store_true",
                   help="also dump WeekData as .json next to .pptx")
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    for noisy in ("httpx", "httpcore", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    print("=" * 64)
    print(f"TPM AI - Weekly Progress  (window={args.days}d, end={args.end or 'today'})")
    print("=" * 64)

    week = collect_week_data(week_end=args.end, days=args.days)

    print(f"[collect] window: {week.week_start} -> {week.week_end}")
    print(f"          sessions:  {week.n_sessions} "
          f"(active days: {week.n_days_with_activity})")
    print(f"          done/fail: {week.n_done}/{week.n_failed}")
    print(f"          artifacts: {len(week.artifacts)}")
    print(f"          commits:   {len(week.git_commits)}")
    print(f"          briefs:    {len(week.night_briefs)}")
    if week.repeated_failures:
        print(f"          repeated fails: {week.repeated_failures}")

    print("[render] generating slides...")
    pptx_path = generate_slides(week)
    print(f"[ok] saved: {pptx_path}")

    if args.json:
        json_path = pptx_path.with_suffix(".json")
        json_path.write_text(
            json.dumps(week.as_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"[ok] saved: {json_path}")

    print()
    print("=" * 64)
    print(f"Open the .pptx to review:  {pptx_path}")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
