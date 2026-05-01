"""
power_monitor.py - battery-aware scheduling
ref: MASTER_PLAN_v5.md § 3.3

Modes:
  desktop_mode      → no battery (เครื่องเสียบปลั๊กตลอด)
  normal_mode       → battery > 50% หรือ plugged
  conservative_mode → battery 20-50%, unplugged → หยุด night cycle, postpone heavy
  emergency_mode    → battery 10-20%, unplugged → checkpoint + ready to shutdown
  shutdown_now      → battery < 10%, unplugged → graceful shutdown

Usage:
  python scripts/power_monitor.py             # daemon
  python scripts/power_monitor.py --check     # one-shot
  python scripts/power_monitor.py --status    # JSON
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

try:
    import psutil
except ImportError:
    psutil = None

POLL_INTERVAL_SEC = 30
LOG_DIR = Path(__file__).resolve().parent.parent / "logs" / "power"
LOG_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class PowerReading:
    timestamp: str
    has_battery: bool
    battery_pct: float | None
    plugged: bool | None
    secs_left: int | None
    mode: str           # desktop_mode | normal_mode | conservative_mode | emergency_mode | shutdown_now
    actions: list[str]


def assess() -> PowerReading:
    if psutil is None:
        return PowerReading(
            timestamp=datetime.now().isoformat(timespec="seconds"),
            has_battery=False,
            battery_pct=None,
            plugged=None,
            secs_left=None,
            mode="desktop_mode",
            actions=["psutil not installed - assume desktop"],
        )

    battery = psutil.sensors_battery()
    if battery is None:
        return PowerReading(
            timestamp=datetime.now().isoformat(timespec="seconds"),
            has_battery=False,
            battery_pct=None,
            plugged=None,
            secs_left=None,
            mode="desktop_mode",
            actions=[],
        )

    pct = float(battery.percent)
    plugged = bool(battery.power_plugged)
    secs = battery.secsleft if battery.secsleft != psutil.POWER_TIME_UNLIMITED else None

    if plugged:
        mode = "normal_mode"
        actions: list[str] = []
    elif pct > 50:
        mode = "normal_mode"
        actions = []
    elif pct > 20:
        mode = "conservative_mode"
        actions = ["pause_night_cycle", "postpone_heavy_models", "reduce_polling_interval"]
    elif pct > 10:
        mode = "emergency_mode"
        actions = [
            "checkpoint_all_state",
            "stop_non_essential",
            "warn_user_save_work",
            "preempt_unloads",
        ]
    else:
        mode = "shutdown_now"
        actions = [
            "graceful_shutdown",
            "final_checkpoint",
            "auto_commit_git",
            "stop_all_services",
        ]

    return PowerReading(
        timestamp=datetime.now().isoformat(timespec="seconds"),
        has_battery=True,
        battery_pct=pct,
        plugged=plugged,
        secs_left=secs,
        mode=mode,
        actions=actions,
    )


def log_reading(r: PowerReading) -> None:
    today = datetime.now().strftime("%Y%m%d")
    log_file = LOG_DIR / f"power_{today}.jsonl"
    with log_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")


def run_daemon() -> None:
    logging.info("power_monitor daemon started - interval=%ss", POLL_INTERVAL_SEC)
    last_mode = None
    while True:
        try:
            r = assess()
            log_reading(r)
            if r.mode != last_mode:
                logging.warning(
                    "POWER MODE → %s | battery=%s%% plugged=%s | actions=%s",
                    r.mode,
                    r.battery_pct,
                    r.plugged,
                    ",".join(r.actions) or "-",
                )
                last_mode = r.mode
            if r.mode == "shutdown_now":
                logging.error("BATTERY CRITICAL - exiting daemon (orchestrator should act)")
                break
            time.sleep(POLL_INTERVAL_SEC)
        except KeyboardInterrupt:
            break
        except Exception as e:  # noqa: BLE001
            logging.error("power_monitor error: %s", e)
            time.sleep(POLL_INTERVAL_SEC)


def main() -> int:
    parser = argparse.ArgumentParser(description="TPM AI power monitor")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    if args.status:
        r = assess()
        print(json.dumps(asdict(r), ensure_ascii=False, indent=2))
        return 0 if r.mode in ("desktop_mode", "normal_mode") else 1

    if args.check:
        r = assess()
        bat = f"{r.battery_pct:.0f}%" if r.battery_pct is not None else "n/a"
        print(f"[{r.mode}] battery={bat} plugged={r.plugged} actions={','.join(r.actions) or '-'}")
        return 0

    run_daemon()
    return 0


if __name__ == "__main__":
    sys.exit(main())
