"""
night_cycle.py - run the night-time self-correction routine
ref: MASTER_PLAN_v5.md § 15

Default behavior:
    1. Find today's sessions
    2. Replay each (using same model unless --heavy)
    3. Diff against original (compare_runs)
    4. Audit prompt budgets statically
    5. Audit runtime stats (latency / failure modes)
    6. Render morning brief to .tpm_context/night_cycle/morning_brief/<date>.md

Usage:
    python scripts/night_cycle.py                    # today, same model
    python scripts/night_cycle.py --date 2026-05-02  # specific date
    python scripts/night_cycle.py --heavy            # use Qwen3-14B for replay
    python scripts/night_cycle.py --no-replay        # skip replay (audit only)
"""
from __future__ import annotations

import argparse
import ctypes
import logging
import os
import platform
import sys
from datetime import datetime, timezone
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

from tpm_night import (  # noqa: E402
    audit_prompts,
    audit_runtime,
    list_sessions,
    render_brief,
    replay_session,
    write_brief,
)
from tpm_night.discrepancy import compare_runs  # noqa: E402
from tpm_search.quota import status as quota_status  # noqa: E402

log = logging.getLogger(__name__)


# ─── Windows sleep prevention (G-04 patch) ───────────────────────────────────
_ES_CONTINUOUS      = 0x80000000
_ES_SYSTEM_REQUIRED = 0x00000001

def _prevent_sleep() -> bool:
    """Keep Windows awake for the night cycle duration. No-op on non-Windows."""
    if platform.system() != "Windows":
        return False
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(
            _ES_CONTINUOUS | _ES_SYSTEM_REQUIRED
        )
        log.info("sleep-prevention: Windows will not sleep during night cycle")
        return True
    except Exception as exc:
        log.warning("sleep-prevention: failed to set execution state: %s", exc)
        return False

def _restore_sleep() -> None:
    """Re-enable normal sleep when night cycle finishes."""
    if platform.system() != "Windows":
        return
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(_ES_CONTINUOUS)
    except Exception:
        pass
# ─────────────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="TPM AI Night Cycle")
    parser.add_argument(
        "--date",
        default=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        help="date to audit (default: today UTC)",
    )
    parser.add_argument(
        "--heavy",
        action="store_true",
        help="use heavier model for replay (Qwen3-14B / Qwen3-27B)",
    )
    parser.add_argument(
        "--no-replay",
        action="store_true",
        help="skip replay step (audit only)",
    )
    parser.add_argument(
        "--max-replays",
        type=int,
        default=10,
        help="cap replay count to keep night cycle bounded",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    for noisy in ("httpx", "httpcore", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    print("=" * 64)
    print(f"TPM AI Night Cycle - date={args.date}")
    print("=" * 64)

    # ---- 0. Prevent Windows sleep for duration of night cycle (G-04) ----
    _prevent_sleep()

    # ---- 1. Load sessions ----
    sessions = list_sessions(date=args.date)
    print(f"[load] {len(sessions)} sessions for {args.date}")
    if not sessions:
        print("[skip] no sessions to audit")
        # Still write a brief so user sees something
        brief = render_brief(
            date=args.date,
            sessions=[],
            runtime_stats=audit_runtime([]),
            prompt_findings=audit_prompts(),
            replay_results=[],
            quota_snapshot=quota_status(),
        )
        path = write_brief(args.date, brief)
        print(f"[brief] {path}")
        return 0

    # ---- 2. Audit prompts (static, no LLM needed) ----
    print("[audit] static prompt-size scan...")
    prompt_findings = audit_prompts()
    n_over = sum(1 for f in prompt_findings if f.severity in ("warn", "error"))
    print(f"  -> {len(prompt_findings)} prompts scanned, {n_over} over budget")

    # ---- 3. Audit runtime (over saved sessions) ----
    print("[audit] runtime stats...")
    runtime_stats = audit_runtime(sessions)
    print(
        f"  -> done={runtime_stats.n_done} fail={runtime_stats.n_failed} "
        f"p90={runtime_stats.p90()/1000:.1f}s "
        f"cold_starts={runtime_stats.cold_starts}"
    )

    # ---- 4. Replay (optional, expensive) ----
    replay_results: list[dict] = []
    if not args.no_replay:
        # Heuristic: replay sessions that ended in DONE (skip failures)
        # Cap at --max-replays to keep night work bounded
        candidates = [s for s in sessions if s.final_phase == "done"][: args.max_replays]
        print(f"[replay] running {len(candidates)} sessions...")
        replay_model = None
        if args.heavy:
            replay_model = os.getenv("TPM_NIGHT_HEAVY_MODEL", "qwen3:14b-instruct-q4_K_M")
            print(f"  using heavy model: {replay_model}")

        for i, rec in enumerate(candidates, 1):
            print(f"  [{i}/{len(candidates)}] {rec.session_id[:8]} {rec.user_request[:50]!r}")
            try:
                replay_final = replay_session(rec, model=replay_model, persist=False)
                diffs = compare_runs(rec, replay_final)
                replay_results.append({
                    "session_id": rec.session_id,
                    "user_request": rec.user_request,
                    "discrepancies": diffs,
                    "replay_phase": (
                        replay_final.phase.value if replay_final and hasattr(replay_final, "phase")
                        else None
                    ),
                })
                err_n = sum(1 for d in diffs if d.severity == "error")
                warn_n = sum(1 for d in diffs if d.severity == "warn")
                print(f"      diffs: {err_n} error / {warn_n} warn / "
                      f"{len(diffs)-err_n-warn_n} info")
            except Exception as e:  # noqa: BLE001
                log.error("replay failed for %s: %s", rec.session_id, e)
                replay_results.append({
                    "session_id": rec.session_id,
                    "user_request": rec.user_request,
                    "discrepancies": [],
                    "replay_phase": "exception",
                    "exception": str(e),
                })

    # ---- 5. Render brief ----
    print("[brief] rendering markdown...")
    brief = render_brief(
        date=args.date,
        sessions=sessions,
        runtime_stats=runtime_stats,
        prompt_findings=prompt_findings,
        replay_results=replay_results,
        quota_snapshot=quota_status(),
    )
    path = write_brief(args.date, brief)
    print(f"[brief] saved -> {path}")
    print()
    print("=" * 64)
    print(f"Night Cycle complete. Read brief: {path}")
    print("=" * 64)

    # ---- Restore normal sleep settings (G-04) ----
    _restore_sleep()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
