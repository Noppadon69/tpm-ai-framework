"""
demo_vibration.py - synthetic bearing-fault vibration analysis (endaq + scipy)

Companion to demo_drivetrain.py. Where drivetrain.py models what we EXPECT
the rotating system to do (natural frequencies, FRF), this script simulates
what we'd MEASURE on the drum shaft and shows how the analysis picks out
a bearing fault signature.

Scenario:
  Wash drum spinning at f_r = 24 Hz (mid spin). Outer-race fault on the
  drum-side bearing (a 6204 deep-groove, geometry below). Accelerometer
  glued near the bearing housing samples at 8 kHz for 5 s.

Signal model:
  a(t) =   A_unbalance * sin(2 pi f_r t)                    # 1x rotational
         + A_bpfo * impulse_train(BPFO) * envelope(f_r)     # bearing fault
         + sigma * white noise                              # background

Output:
  output/demo/vibration_raw.png        - time-domain trace (first 0.5 s)
  output/demo/vibration_spectrum.png   - FFT magnitude + envelope spectrum
                                          with BPFO/BPFI/BSF/FTF/1x markers
  console table                        - bearing fault frequency cheatsheet
                                          + dominant peaks found

If the envelope spectrum peaks within +/- 2 percent of the calculated BPFO
the script flags "consistent with outer-race fault" (the classic Mide /
condition-monitoring teaching example).

Pre-internship portfolio piece per 2026-05-13 plan. Self-contained; not
in the production worker pipeline. Day-1 talking point: 'with a measured
accelerometer trace I can pull bearing fault signatures from background
rotational vibration.'
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from scipy.signal import hilbert
from endaq.calc.fft import aggregate_fft  # endaq integration touch


# ---------------------------------------------------------------------------
# Bearing geometry: SKF 6204 deep-groove (standard washing-machine drum bearing)
# ---------------------------------------------------------------------------
N_BALLS = 8
BALL_DIAM_MM = 7.94
PITCH_DIAM_MM = 33.5
CONTACT_ANGLE_DEG = 0.0  # deep groove

# Operating condition
F_R_HZ = 24.0   # drum spin speed (mid wash)
FS_HZ = 8000.0  # accelerometer sample rate
T_TOTAL_S = 5.0


def bearing_fault_freqs(f_r: float) -> dict[str, float]:
    """Standard ball-bearing fault frequencies."""
    n = N_BALLS
    d = BALL_DIAM_MM
    D = PITCH_DIAM_MM
    alpha = np.deg2rad(CONTACT_ANGLE_DEG)
    ratio = d / D * np.cos(alpha)
    bpfo = (n / 2.0) * f_r * (1.0 - ratio)
    bpfi = (n / 2.0) * f_r * (1.0 + ratio)
    bsf  = (D / (2.0 * d)) * f_r * (1.0 - ratio**2)
    ftf  = (f_r / 2.0) * (1.0 - ratio)
    return {"FTF": ftf, "BSF": bsf, "BPFO": bpfo, "BPFI": bpfi}


def synthesize_signal(f_r: float, fault_freq: float, fs: float, t_total: float,
                      seed: int = 7) -> pd.DataFrame:
    """Return acceleration trace as pandas Series indexed by time (s)."""
    rng = np.random.default_rng(seed)
    t = np.arange(0.0, t_total, 1.0 / fs)

    # 1x rotational unbalance (cleanly sinusoidal at f_r)
    a_unbalance = 0.30 * np.sin(2.0 * np.pi * f_r * t)

    # bearing fault: damped sinusoidal impulses at fault_freq, modulated by
    # cage/shaft motion (very simplified physics, enough for the demo)
    impulse_period = 1.0 / fault_freq
    a_fault = np.zeros_like(t)
    # ringing of bearing housing at ~3 kHz when struck by defect
    ring_freq = 3000.0
    ring_decay = 800.0
    for k in range(int(t_total / impulse_period) + 1):
        t0 = (k + 0.5) * impulse_period  # half-cycle offset
        dt = t - t0
        mask = dt >= 0.0
        ring = np.exp(-ring_decay * dt[mask]) * np.sin(2.0 * np.pi * ring_freq * dt[mask])
        # slight amplitude modulation by 1x (load zone passage)
        amp = 0.55 * (1.0 + 0.4 * np.cos(2.0 * np.pi * f_r * t0))
        a_fault[mask] += amp * ring

    # broadband white noise
    a_noise = 0.05 * rng.standard_normal(t.size)

    a = a_unbalance + a_fault + a_noise
    return pd.DataFrame({"accel_g": a}, index=pd.Index(t, name="time_s"))


def envelope_spectrum(sig: np.ndarray, fs: float) -> tuple[np.ndarray, np.ndarray]:
    """Hilbert envelope + magnitude FFT of the envelope."""
    analytic = hilbert(sig - sig.mean())
    env = np.abs(analytic)
    env = env - env.mean()
    n = env.size
    f = np.fft.rfftfreq(n, d=1.0 / fs)
    mag = np.abs(np.fft.rfft(env)) / n
    return f, mag


def dominant_peaks(freqs: np.ndarray, mag: np.ndarray, top: int = 5,
                   min_hz: float = 5.0, max_hz: float = 500.0) -> list[tuple[float, float]]:
    """Return top-N peaks by magnitude in [min_hz, max_hz]."""
    sel = (freqs >= min_hz) & (freqs <= max_hz)
    f_sel = freqs[sel]
    m_sel = mag[sel]
    idx_sorted = np.argsort(m_sel)[::-1]
    chosen: list[tuple[float, float]] = []
    for idx in idx_sorted:
        f = float(f_sel[idx])
        if all(abs(f - p[0]) > 2.0 for p in chosen):  # 2 Hz separation
            chosen.append((f, float(m_sel[idx])))
        if len(chosen) >= top:
            break
    return chosen


def write_raw_plot(df: pd.DataFrame, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 3.2))
    t = df.index.values
    a = df["accel_g"].values
    mask = t <= 0.5
    ax.plot(t[mask], a[mask], lw=0.6, color="#222")
    ax.set_xlabel("time (s)")
    ax.set_ylabel("accel (g)")
    ax.set_title(f"Synthetic accelerometer trace - drum at {F_R_HZ:.0f} Hz, BPFO fault")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def write_spectrum_plot(freqs_raw: np.ndarray, mag_raw: np.ndarray,
                        freqs_env: np.ndarray, mag_env: np.ndarray,
                        fault_freqs: dict[str, float], out_path: Path) -> None:
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7.5, 6), sharex=True)
    band_hi = 500.0

    def overlay_markers(ax, fault_freqs):
        colors = {"FTF": "#117733", "BSF": "#332288", "BPFO": "#cc6677", "BPFI": "#ddaa33"}
        for name, f in fault_freqs.items():
            if f < band_hi:
                ax.axvline(f, color=colors[name], ls="--", lw=0.8, alpha=0.8)
                ax.text(f, ax.get_ylim()[1] * 0.92, name, color=colors[name],
                        ha="center", fontsize=8, rotation=0)
        ax.axvline(F_R_HZ, color="#666", ls=":", lw=0.8)
        ax.text(F_R_HZ, ax.get_ylim()[1] * 0.92, "1x", color="#666", ha="center", fontsize=8)

    sel = freqs_raw <= band_hi
    ax1.semilogy(freqs_raw[sel], mag_raw[sel], color="#222", lw=0.8)
    ax1.set_ylabel("|FFT| (g, log)")
    ax1.set_title("Raw acceleration spectrum")
    ax1.grid(True, which="both", alpha=0.3)
    overlay_markers(ax1, fault_freqs)

    sel_e = freqs_env <= band_hi
    ax2.semilogy(freqs_env[sel_e], mag_env[sel_e], color="#222", lw=0.8)
    ax2.set_xlabel("frequency (Hz)")
    ax2.set_ylabel("|FFT of envelope| (log)")
    ax2.set_title("Envelope spectrum (Hilbert) - bearing fault diagnostic")
    ax2.grid(True, which="both", alpha=0.3)
    overlay_markers(ax2, fault_freqs)

    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def main() -> int:
    out_dir = Path("output/demo")
    out_dir.mkdir(parents=True, exist_ok=True)

    fault_freqs = bearing_fault_freqs(F_R_HZ)
    bpfo = fault_freqs["BPFO"]

    print("=" * 60)
    print(f"Bearing fault analysis - 6204 deep-groove @ {F_R_HZ:.0f} Hz spin")
    print("=" * 60)
    print("Bearing geometry:")
    print(f"  N balls={N_BALLS}, ball diam={BALL_DIAM_MM} mm, pitch diam={PITCH_DIAM_MM} mm")
    print(f"  contact angle={CONTACT_ANGLE_DEG} deg")
    print()
    print("Fault frequencies (theoretical):")
    for name, f in fault_freqs.items():
        print(f"  {name:5s} = {f:7.2f} Hz")
    print()

    # Build signal with seeded BPFO fault
    df = synthesize_signal(f_r=F_R_HZ, fault_freq=bpfo, fs=FS_HZ, t_total=T_TOTAL_S)
    a = df["accel_g"].values

    # Raw spectrum via endaq.calc.fft (touches the integration, output is df)
    raw_fft_df = aggregate_fft(df)
    freqs_raw = raw_fft_df.index.values.astype(float)
    mag_raw = raw_fft_df["accel_g"].values.astype(float)

    # Envelope spectrum (scipy)
    freqs_env, mag_env = envelope_spectrum(a, FS_HZ)

    print("Top-5 peaks in raw spectrum (5-500 Hz):")
    for f, m in dominant_peaks(freqs_raw, mag_raw, top=5):
        print(f"  {f:7.2f} Hz  mag={m:.4f}")
    print()
    print("Top-5 peaks in envelope spectrum (5-500 Hz):")
    env_peaks = dominant_peaks(freqs_env, mag_env, top=5)
    for f, m in env_peaks:
        marker = ""
        if abs(f - bpfo) / bpfo <= 0.02:
            marker = "  <- matches BPFO (outer-race fault signature)"
        elif abs(f - F_R_HZ) / F_R_HZ <= 0.02:
            marker = "  <- 1x rotational unbalance"
        print(f"  {f:7.2f} Hz  mag={m:.4f}{marker}")
    print()

    # Overall verdict
    has_bpfo = any(abs(f - bpfo) / bpfo <= 0.02 for f, _ in env_peaks)
    if has_bpfo:
        print(f"VERDICT: envelope spectrum peak near BPFO={bpfo:.1f} Hz")
        print("         consistent with outer-race bearing defect")
    else:
        print("VERDICT: no clean BPFO peak; check signal amplitude or sample rate")
    print()

    raw_png = out_dir / "vibration_raw.png"
    spec_png = out_dir / "vibration_spectrum.png"
    write_raw_plot(df, raw_png)
    write_spectrum_plot(freqs_raw, mag_raw, freqs_env, mag_env, fault_freqs, spec_png)
    print(f"Wrote {raw_png}")
    print(f"Wrote {spec_png}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
