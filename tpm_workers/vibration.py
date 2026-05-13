"""
tpm_workers.vibration - accelerometer time-series -> bearing fault verdict

Pipeline (mirrors demo_vibration.py but production-shaped):
  1. Load accelerometer CSV/TSV (pandas)
  2. Theoretical bearing fault frequencies from geometry
  3. Raw FFT magnitude spectrum (endaq.calc.fft.aggregate_fft)
  4. Hilbert envelope spectrum (scipy.signal.hilbert)
  5. Peak detection + automatic verdict against BPFO/BPFI/BSF/FTF
  6. .md audit trail to output/vibration/<session_id>.md

Worker contract: tpm_workers.base.WorkerInput / WorkerResult.

Input file format (CSV, header row required):
    time_s,accel_g
    0.0000,0.001
    0.000125,0.012
    ...
or any single-column accel trace with a time index (if no time column,
fall back to extras["fs_hz"] for sample rate).

Required extras keys (with sensible defaults):
    accel_csv      : str, path to acceleration CSV (REQUIRED)
    f_r_hz         : float, shaft rotation frequency in Hz (REQUIRED)
    bearing        : str | dict, one of presets or full geometry dict.
                     Presets: "6204", "6205", "6206" (deep-groove washing-
                     machine drum bearings).
    fs_hz          : float, sample rate; only used if CSV has no time col

Output WorkerResult.metrics keys:
    dominant_raw_hz       : float
    bpfo_theoretical_hz   : float
    envelope_peak_hz      : float
    envelope_peak_error_pct : float
    fault_verdict         : "outer_race" | "inner_race" | "ball" | "cage" | "none"
    confidence            : 0..1
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd
from scipy.signal import hilbert

from tpm_workers.base import WorkerInput, WorkerResult, WorkerStep, WorkerType

log = logging.getLogger(__name__)


# ============================================================
# Bearing presets (washing-machine drum-side)
# ============================================================
# Geometry: n_balls, ball diameter [mm], pitch diameter [mm], contact angle [deg]
BEARING_PRESETS: dict[str, dict[str, float]] = {
    "6204": {"n_balls": 8, "ball_diam_mm": 7.94, "pitch_diam_mm": 33.5, "angle_deg": 0.0},
    "6205": {"n_balls": 9, "ball_diam_mm": 7.94, "pitch_diam_mm": 39.0, "angle_deg": 0.0},
    "6206": {"n_balls": 9, "ball_diam_mm": 9.53, "pitch_diam_mm": 46.0, "angle_deg": 0.0},
}


def bearing_fault_freqs(geom: dict[str, float], f_r_hz: float) -> dict[str, float]:
    """Standard ball-bearing fault frequencies."""
    n = float(geom["n_balls"])
    d = float(geom["ball_diam_mm"])
    D = float(geom["pitch_diam_mm"])
    alpha = np.deg2rad(float(geom.get("angle_deg", 0.0)))
    r = d / D * np.cos(alpha)
    return {
        "BPFO": (n / 2.0) * f_r_hz * (1.0 - r),
        "BPFI": (n / 2.0) * f_r_hz * (1.0 + r),
        "BSF":  (D / (2.0 * d)) * f_r_hz * (1.0 - r**2),
        "FTF":  (f_r_hz / 2.0) * (1.0 - r),
    }


# ============================================================
# Spectrum helpers
# ============================================================
def envelope_spectrum(sig: np.ndarray, fs: float) -> tuple[np.ndarray, np.ndarray]:
    """Hilbert envelope + magnitude FFT of the envelope (single-sided)."""
    analytic = hilbert(sig - np.mean(sig))
    env = np.abs(analytic)
    env = env - np.mean(env)
    n = env.size
    f = np.fft.rfftfreq(n, d=1.0 / fs)
    mag = np.abs(np.fft.rfft(env)) / n
    return f, mag


def raw_spectrum(sig: np.ndarray, fs: float) -> tuple[np.ndarray, np.ndarray]:
    n = sig.size
    f = np.fft.rfftfreq(n, d=1.0 / fs)
    mag = np.abs(np.fft.rfft(sig - np.mean(sig))) / n
    return f, mag


def dominant_peak_in_band(freqs: np.ndarray, mag: np.ndarray,
                          lo_hz: float, hi_hz: float) -> tuple[float, float]:
    sel = (freqs >= lo_hz) & (freqs <= hi_hz)
    if not sel.any():
        return float("nan"), float("nan")
    idx = int(np.argmax(mag[sel]))
    return float(freqs[sel][idx]), float(mag[sel][idx])


# ============================================================
# Loader + worker
# ============================================================
def _load_accel(csv_path: Path, fallback_fs_hz: Optional[float]) -> tuple[np.ndarray, float]:
    """Return (acceleration array, sample rate Hz)."""
    df = pd.read_csv(csv_path)
    cols = [c.lower() for c in df.columns]
    if "accel_g" in cols:
        a = df[df.columns[cols.index("accel_g")]].to_numpy(dtype=float)
    elif "accel" in cols:
        a = df[df.columns[cols.index("accel")]].to_numpy(dtype=float)
    else:
        # take first numeric column
        a = df.iloc[:, 0].to_numpy(dtype=float)

    if "time_s" in cols:
        t = df[df.columns[cols.index("time_s")]].to_numpy(dtype=float)
        if t.size >= 2:
            dt = float(np.median(np.diff(t)))
            fs = 1.0 / dt if dt > 0 else (fallback_fs_hz or 1000.0)
            return a, fs
    if fallback_fs_hz:
        return a, float(fallback_fs_hz)
    raise ValueError("no time_s column and no extras['fs_hz'] provided")


def _classify_verdict(env_peak_hz: float, fault_freqs: dict[str, float],
                      tol_pct: float = 2.0,
                      max_harmonic: int = 3) -> tuple[str, float]:
    """
    Match envelope peak to nearest fault frequency OR its harmonics within
    tol_pct. Bearing-fault signatures often show stronger 2x or 3x harmonics
    than the fundamental in short/noisy traces; checking harmonics gives a
    robust verdict without forcing the user to collect a long sample.
    """
    best_name = "none"
    best_err = float("inf")
    best_harmonic = 1
    for name, f in fault_freqs.items():
        if f <= 0:
            continue
        for k in range(1, max_harmonic + 1):
            target = k * f
            err = abs(env_peak_hz - target) / target * 100.0
            if err < best_err:
                best_err = err
                best_name = name
                best_harmonic = k
    if best_err <= tol_pct:
        conf_map = {"BPFO": 0.85, "BPFI": 0.75, "BSF": 0.65, "FTF": 0.55}
        conf = conf_map.get(best_name, 0.50)
        if best_harmonic > 1:
            conf -= 0.02 * (best_harmonic - 1)
        return _verdict_label(best_name), max(conf, 0.30)
    return "none", 0.30


def _verdict_label(fault_name: str) -> str:
    return {"BPFO": "outer_race", "BPFI": "inner_race",
            "BSF": "ball", "FTF": "cage"}.get(fault_name, "none")


def _write_audit(out_path: Path, *, csv_path: Path, f_r_hz: float,
                 bearing_name: str, geom: dict[str, float],
                 fault_freqs: dict[str, float], dom_raw_hz: float,
                 env_peak_hz: float, env_peak_mag: float,
                 verdict: str, confidence: float) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Vibration analysis - {csv_path.name}",
        "",
        f"- Bearing: **{bearing_name}** (n={int(geom['n_balls'])}, "
        f"d={geom['ball_diam_mm']} mm, D={geom['pitch_diam_mm']} mm)",
        f"- Shaft speed: **{f_r_hz:.2f} Hz**",
        "",
        "## Theoretical fault frequencies (Hz)",
        "",
        "| Mode | Frequency |",
        "|---|---|",
    ]
    for name in ("FTF", "BSF", "BPFO", "BPFI"):
        lines.append(f"| {name} | {fault_freqs[name]:.2f} |")
    lines += [
        "",
        "## Measured peaks",
        "",
        f"- Raw spectrum dominant (5-500 Hz): **{dom_raw_hz:.2f} Hz**",
        f"- Envelope spectrum peak: **{env_peak_hz:.2f} Hz** (mag={env_peak_mag:.4f})",
        "",
        "## Verdict",
        "",
        f"- **{verdict}** (confidence {confidence:.2f})",
        "",
    ]
    out_path.write_text("\n".join(lines), encoding="utf-8")


def run_vibration_worker(inp: WorkerInput) -> WorkerResult:
    result = WorkerResult(worker_type=WorkerType.VIBRATION, success=False)
    extras = inp.extras or {}

    # ---- Step 1: validate inputs ----
    step1 = WorkerStep(name="validate_inputs")
    csv_arg = extras.get("accel_csv")
    if not csv_arg:
        step1.finish(success=False, error="extras['accel_csv'] required")
        result.add_step(step1)
        result.summary = "vibration: missing accel_csv"
        return result
    csv_path = Path(csv_arg)
    if not csv_path.is_file():
        step1.finish(success=False, error=f"file not found: {csv_path}")
        result.add_step(step1)
        result.summary = f"vibration: file missing {csv_path}"
        return result

    f_r_hz = extras.get("f_r_hz")
    if not f_r_hz or float(f_r_hz) <= 0:
        step1.finish(success=False, error="extras['f_r_hz'] required (>0)")
        result.add_step(step1)
        result.summary = "vibration: missing or bad f_r_hz"
        return result

    bearing = extras.get("bearing", "6204")
    if isinstance(bearing, str):
        geom = BEARING_PRESETS.get(bearing)
        if geom is None:
            step1.finish(success=False, error=f"unknown bearing preset {bearing!r}")
            result.add_step(step1)
            result.summary = f"vibration: unknown bearing {bearing}"
            return result
        bearing_name = bearing
    elif isinstance(bearing, dict):
        geom = bearing
        bearing_name = "custom"
    else:
        step1.finish(success=False, error="extras['bearing'] must be str or dict")
        result.add_step(step1)
        result.summary = "vibration: bad bearing arg"
        return result
    step1.finish(success=True)
    step1.notes.append(f"bearing={bearing_name}, f_r={f_r_hz} Hz")
    result.add_step(step1)

    # ---- Step 2: load signal ----
    step2 = WorkerStep(name="load_signal")
    try:
        a, fs = _load_accel(csv_path, extras.get("fs_hz"))
    except Exception as e:  # noqa: BLE001
        step2.finish(success=False, error=f"{type(e).__name__}: {e}")
        result.add_step(step2)
        result.summary = f"vibration: load failed {e}"
        return result
    step2.finish(success=True)
    step2.notes.append(f"samples={a.size}, fs={fs:.1f} Hz, duration={a.size/fs:.2f} s")
    result.add_step(step2)

    # ---- Step 3: compute spectra ----
    step3 = WorkerStep(name="compute_spectra")
    fault_freqs = bearing_fault_freqs(geom, float(f_r_hz))
    fr, mr = raw_spectrum(a, fs)
    fe, me = envelope_spectrum(a, fs)
    dom_raw_hz, _ = dominant_peak_in_band(fr, mr, 5.0, 500.0)
    env_peak_hz, env_peak_mag = dominant_peak_in_band(fe, me, 5.0, 500.0)
    step3.finish(success=True)
    step3.notes.append(
        f"raw_dom={dom_raw_hz:.2f} Hz, env_peak={env_peak_hz:.2f} Hz, "
        f"BPFO={fault_freqs['BPFO']:.2f} Hz"
    )
    result.add_step(step3)

    # ---- Step 4: classify + write audit ----
    step4 = WorkerStep(name="classify_and_audit")
    verdict, confidence = _classify_verdict(env_peak_hz, fault_freqs)
    out_dir = inp.output_dir if isinstance(inp.output_dir, Path) else Path(inp.output_dir)
    out_md = out_dir / "vibration" / f"{inp.session_id or csv_path.stem}.md"
    try:
        _write_audit(
            out_md, csv_path=csv_path, f_r_hz=float(f_r_hz),
            bearing_name=bearing_name, geom=geom, fault_freqs=fault_freqs,
            dom_raw_hz=dom_raw_hz, env_peak_hz=env_peak_hz,
            env_peak_mag=env_peak_mag, verdict=verdict, confidence=confidence,
        )
    except Exception as e:  # noqa: BLE001
        step4.finish(success=False, error=f"audit write failed: {e}")
        result.add_step(step4)
        result.summary = f"vibration: audit write failed {e}"
        return result
    step4.finish(success=True)
    result.add_step(step4)

    # ---- Pack metrics ----
    # Report error against the BEST-MATCHED harmonic, not just fundamental,
    # so the metric reflects what the verdict actually used.
    name_to_freq = {"outer_race": "BPFO", "inner_race": "BPFI",
                    "ball": "BSF", "cage": "FTF"}
    matched_freq_name = name_to_freq.get(verdict)
    matched_harmonic = 1
    if matched_freq_name and fault_freqs[matched_freq_name] > 0:
        f0 = fault_freqs[matched_freq_name]
        # find k minimizing | env_peak - k*f0 | for k in 1..3
        k_best = min((1, 2, 3), key=lambda k: abs(env_peak_hz - k * f0))
        matched_harmonic = k_best
        err_vs_matched = 100.0 * abs(env_peak_hz - k_best * f0) / (k_best * f0)
    else:
        err_vs_matched = float("nan")
    err_vs_bpfo = (
        100.0 * abs(env_peak_hz - fault_freqs["BPFO"]) / fault_freqs["BPFO"]
        if fault_freqs["BPFO"] > 0 else float("nan")
    )
    result.metrics = {
        "dominant_raw_hz": dom_raw_hz,
        "bpfo_theoretical_hz": fault_freqs["BPFO"],
        "envelope_peak_hz": env_peak_hz,
        "envelope_peak_error_vs_bpfo_pct": err_vs_bpfo,
        "envelope_peak_error_vs_matched_pct": err_vs_matched,
        "matched_harmonic": matched_harmonic,
        "fault_verdict": verdict,
        "samples": int(a.size),
        "fs_hz": float(fs),
    }
    result.confidence = float(confidence)
    result.success = True
    result.output_files.append(str(out_md))
    result.summary = (
        f"vibration: verdict={verdict} (conf={confidence:.2f}); "
        f"env_peak={env_peak_hz:.2f} Hz vs BPFO={fault_freqs['BPFO']:.2f} Hz"
    )
    return result
