"""
thermal_guard.py - CPU/GPU thermal monitor
ref: MASTER_PLAN_v5.md § 3.4

Behavior:
  CPU > 75 deg C / GPU > 75 deg C  → log warning
  CPU > 80 deg C / GPU > 82 deg C  → slow down (factor 0.5)
  CPU > 85 deg C / GPU > 87 deg C  → pause heavy tasks + notify

Usage:
  python scripts/thermal_guard.py             # daemon
  python scripts/thermal_guard.py --check     # one-shot
  python scripts/thermal_guard.py --status    # JSON status
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

# ----- soft imports (degrade gracefully if not installed) ----
try:
    import psutil
except ImportError:
    psutil = None

try:
    import GPUtil
except ImportError:
    GPUtil = None

# ============================================================
# Config
# ============================================================
THRESHOLDS = {
    "cpu_warn": 75,
    "cpu_throttle": 80,
    "cpu_critical": 85,
    "gpu_warn": 75,
    "gpu_throttle": 82,
    "gpu_critical": 87,
}

POLL_INTERVAL_SEC = 10
LOG_DIR = Path(__file__).resolve().parent.parent / "logs" / "thermal"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# Data model
# ============================================================
@dataclass
class ThermalReading:
    timestamp: str
    cpu_temp_c: float | None
    gpu_temp_c: float | None
    cpu_load_pct: float | None
    gpu_load_pct: float | None
    state: str            # OK | WARN | THROTTLE | CRITICAL | UNKNOWN
    action: str           # none | log_warn | slow_down | pause_heavy
    notes: list[str]


# ============================================================
# Sensors
# ============================================================
def read_cpu_temp() -> float | None:
    """
    Try multiple sources:
    - psutil.sensors_temperatures (Linux only)
    - WMI (Windows) - best-effort, often returns None on consumer laptops
    """
    if psutil is None:
        return None

    if hasattr(psutil, "sensors_temperatures"):
        try:
            temps = psutil.sensors_temperatures()
        except (AttributeError, NotImplementedError):
            temps = {}

        for key in ("coretemp", "k10temp", "cpu_thermal", "cpu-thermal"):
            if key in temps and temps[key]:
                return temps[key][0].current

    # Windows WMI fallback (best-effort)
    try:
        import wmi  # type: ignore

        w = wmi.WMI(namespace="root\\OpenHardwareMonitor")
        sensors = w.Sensor()
        for s in sensors:
            if s.SensorType == "Temperature" and "CPU" in (s.Name or ""):
                return float(s.Value)
    except Exception:
        pass

    return None


def read_gpu_temp() -> tuple[float | None, float | None]:
    """Returns (temp_c, load_pct) or (None, None)."""
    if GPUtil is None:
        return (None, None)
    try:
        gpus = GPUtil.getGPUs()
        if not gpus:
            return (None, None)
        g = gpus[0]
        return (float(g.temperature), float(g.load) * 100)
    except Exception:
        return (None, None)


def read_cpu_load() -> float | None:
    if psutil is None:
        return None
    return psutil.cpu_percent(interval=0.5)


# ============================================================
# State machine
# ============================================================
def classify(cpu: float | None, gpu: float | None) -> tuple[str, str, list[str]]:
    notes: list[str] = []
    state = "OK"
    action = "none"

    if cpu is None and gpu is None:
        return "UNKNOWN", "none", ["no sensors available"]

    if cpu is not None:
        if cpu >= THRESHOLDS["cpu_critical"]:
            state, action = "CRITICAL", "pause_heavy"
            notes.append(f"CPU {cpu:.1f} deg C ≥ {THRESHOLDS['cpu_critical']} deg C")
        elif cpu >= THRESHOLDS["cpu_throttle"]:
            state, action = max(state, "THROTTLE", key=_severity), "slow_down"
            notes.append(f"CPU {cpu:.1f} deg C ≥ {THRESHOLDS['cpu_throttle']} deg C")
        elif cpu >= THRESHOLDS["cpu_warn"]:
            state, action = max(state, "WARN", key=_severity), "log_warn"
            notes.append(f"CPU {cpu:.1f} deg C ≥ {THRESHOLDS['cpu_warn']} deg C")

    if gpu is not None:
        if gpu >= THRESHOLDS["gpu_critical"]:
            state, action = "CRITICAL", "pause_heavy"
            notes.append(f"GPU {gpu:.1f} deg C ≥ {THRESHOLDS['gpu_critical']} deg C")
        elif gpu >= THRESHOLDS["gpu_throttle"]:
            state = max(state, "THROTTLE", key=_severity)
            if action == "none":
                action = "slow_down"
            notes.append(f"GPU {gpu:.1f} deg C ≥ {THRESHOLDS['gpu_throttle']} deg C")
        elif gpu >= THRESHOLDS["gpu_warn"]:
            state = max(state, "WARN", key=_severity)
            if action == "none":
                action = "log_warn"
            notes.append(f"GPU {gpu:.1f} deg C ≥ {THRESHOLDS['gpu_warn']} deg C")

    return state, action, notes


_SEVERITY = {"OK": 0, "UNKNOWN": 0, "WARN": 1, "THROTTLE": 2, "CRITICAL": 3}


def _severity(s: str) -> int:
    return _SEVERITY.get(s, 0)


# ============================================================
# Reading + logging
# ============================================================
def take_reading() -> ThermalReading:
    cpu = read_cpu_temp()
    gpu, gpu_load = read_gpu_temp()
    state, action, notes = classify(cpu, gpu)
    return ThermalReading(
        timestamp=datetime.now().isoformat(timespec="seconds"),
        cpu_temp_c=cpu,
        gpu_temp_c=gpu,
        cpu_load_pct=read_cpu_load(),
        gpu_load_pct=gpu_load,
        state=state,
        action=action,
        notes=notes,
    )


def log_reading(r: ThermalReading) -> None:
    today = datetime.now().strftime("%Y%m%d")
    log_file = LOG_DIR / f"thermal_{today}.jsonl"
    with log_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")


# ============================================================
# Daemon
# ============================================================
def run_daemon() -> None:
    logging.info("thermal_guard daemon started - interval=%ss", POLL_INTERVAL_SEC)
    while True:
        try:
            r = take_reading()
            log_reading(r)
            if r.state in ("WARN", "THROTTLE", "CRITICAL"):
                logging.warning("[%s] %s | action=%s", r.state, "; ".join(r.notes), r.action)
            time.sleep(POLL_INTERVAL_SEC)
        except KeyboardInterrupt:
            logging.info("thermal_guard stopped by user")
            break
        except Exception as e:  # noqa: BLE001
            logging.error("thermal_guard error: %s", e)
            time.sleep(POLL_INTERVAL_SEC)


# ============================================================
# CLI
# ============================================================
def main() -> int:
    parser = argparse.ArgumentParser(description="TPM AI thermal guard")
    parser.add_argument("--check", action="store_true", help="one-shot reading + exit")
    parser.add_argument("--status", action="store_true", help="JSON status to stdout")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    log_level = logging.WARNING if args.quiet else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s | %(levelname)s | %(message)s")

    if psutil is None:
        logging.warning("psutil not installed - limited sensors")
    if GPUtil is None:
        logging.warning("GPUtil not installed - no GPU readings")

    if args.status:
        r = take_reading()
        print(json.dumps(asdict(r), ensure_ascii=False, indent=2))
        return 0 if r.state in ("OK", "UNKNOWN") else 1

    if args.check:
        r = take_reading()
        print(f"[{r.state}] CPU={r.cpu_temp_c} deg C  GPU={r.gpu_temp_c} deg C  action={r.action}")
        if r.notes:
            for n in r.notes:
                print(f"  - {n}")
        return 0 if r.state in ("OK", "UNKNOWN", "WARN") else 1

    run_daemon()
    return 0


if __name__ == "__main__":
    sys.exit(main())
