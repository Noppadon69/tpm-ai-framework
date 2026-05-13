"""
demo_drivetrain.py - washing-machine drive-train torsional analysis demo

Generic 3-mass torsional model of a top-loader / front-loader drive train:

    Motor (J_motor)  --shaft1, k1--  Coupling (J_coup)  --shaft2, k2--  Drum (J_drum)
       node 0                          node 1                              node 2

What this script produces (all matched to typical Toshiba washing-machine
ranges so the numbers stay defensible if printed and handed to an engineer):

  1) Undamped natural frequencies (modal analysis) in Hz
  2) Torsional FRF magnitude (Bode-ish, no phase) from motor torque input to
     drum angular velocity output, swept 1-300 Hz
  3) Identification of operating spin frequencies (24, 25 Hz wash; 13.3 Hz
     low-spin; 16-23 Hz mid spin) versus resonance peaks - flags any range
     hits within +/- 10 percent of a mode

Outputs:
  output/demo/drivetrain_modal.png       - bar chart of modes
  output/demo/drivetrain_frf.png         - FRF magnitude + spin-region overlay
  console table                          - mode list + clearance flags

Pre-internship portfolio piece per 2026-05-13 plan. Not part of the production
worker pipeline - kept under scripts/ as a self-contained demo. Day-1 it
becomes a talking point: 'I can build a parametric torsional model of any
shaft system you give me.'

Run:
    /d/tpm_workspace/.venv/Scripts/python.exe scripts/demo_drivetrain.py
or  python scripts/demo_drivetrain.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")  # write PNG without DISPLAY
import matplotlib.pyplot as plt

import opentorsion as ot


# ---------------------------------------------------------------------------
# Model parameters (representative; real Toshiba values would override these)
# ---------------------------------------------------------------------------

# Inertias [kg m^2]
J_motor = 0.012   # BLDC rotor + pulley
J_coup  = 0.004   # belt pulley + coupling hub
J_drum  = 0.85    # stainless drum + 7 kg wet laundry mass moment

# Torsional stiffness [N m / rad]
k_shaft1 = 4.5e3   # short motor shaft (stiff)
k_shaft2 = 9.0e2   # belt + drum shaft (compliant - belt dominates)

# Viscous damping [N m s / rad] (light - belts and bearings)
c_shaft1 = 0.05
c_shaft2 = 0.20

# Operating spin frequencies of interest [Hz]
# wash 24-25, distribute 13-16, intermediate spin 18-23, final spin per model
SPIN_FREQS_HZ = {
    "wash":         (23.0, 26.0),
    "distribute":   (13.0, 16.0),
    "intermediate": (18.0, 22.0),
    "final spin":   (22.0, 28.0),
}


def build_assembly() -> ot.Assembly:
    """3-mass torsional model with two flexible shaft elements."""
    disks = [
        ot.Disk(0, I=J_motor),
        ot.Disk(1, I=J_coup),
        ot.Disk(2, I=J_drum),
    ]
    shafts = [
        ot.Shaft(0, 1, k=k_shaft1, I=0.0, c=c_shaft1),
        ot.Shaft(1, 2, k=k_shaft2, I=0.0, c=c_shaft2),
    ]
    return ot.Assembly(shaft_elements=shafts, disk_elements=disks)


def modal_frequencies(asm: ot.Assembly) -> list[float]:
    """Return undamped natural frequencies in Hz, sorted, deduplicated."""
    undamped_rad_s, _damped, _ratios = asm.modal_analysis()
    freqs_hz = np.abs(undamped_rad_s) / (2.0 * np.pi)
    # opentorsion returns complex-conjugate pairs; collapse to unique modes
    uniq = sorted({round(float(f), 4) for f in freqs_hz if f > 1e-6})
    return uniq


def frf_magnitude(asm: ot.Assembly, freqs_hz: np.ndarray) -> np.ndarray:
    """
    Torsional receptance magnitude |theta_drum / T_motor| over a frequency
    sweep. Builds M, C, K from the assembly and solves
        H(omega) = (-omega^2 M + j omega C + K)^-1
    Output: angular displacement at drum DOF (node 2) per unit torque at
    motor DOF (node 0). Convert to velocity-FRF by * j omega if desired.
    """
    M = asm.M
    C = asm.C
    K = asm.K
    n = M.shape[0]
    # input torque applied at node 0, output measured at node 2
    F = np.zeros(n, dtype=complex)
    F[0] = 1.0
    mag = np.zeros_like(freqs_hz, dtype=float)
    for i, f in enumerate(freqs_hz):
        w = 2.0 * np.pi * f
        H = -(w**2) * M + 1j * w * C + K
        try:
            X = np.linalg.solve(H, F)
            mag[i] = np.abs(X[2])
        except np.linalg.LinAlgError:
            mag[i] = np.nan
    return mag


def flag_resonance_in_spin_band(modes_hz: list[float], tol_pct: float = 10.0) -> list[tuple[str, float, float]]:
    """Return [(spin_label, mode_hz, deviation_pct), ...] where any mode falls
    within +/- tol_pct of an operating spin frequency band."""
    hits = []
    for label, (lo, hi) in SPIN_FREQS_HZ.items():
        center = 0.5 * (lo + hi)
        for mode in modes_hz:
            dev_pct = 100.0 * (mode - center) / center
            if abs(dev_pct) <= tol_pct:
                hits.append((label, mode, dev_pct))
    return hits


def write_modal_plot(modes_hz: list[float], out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 3.5))
    if modes_hz:
        idx = list(range(1, len(modes_hz) + 1))
        ax.bar(idx, modes_hz, color="#4477aa", width=0.55)
        for i, f in zip(idx, modes_hz):
            ax.text(i, f, f"{f:.1f} Hz", ha="center", va="bottom", fontsize=9)
    # mark spin bands
    for label, (lo, hi) in SPIN_FREQS_HZ.items():
        ax.axhspan(lo, hi, alpha=0.10, color="#cc6677", lw=0)
        ax.text(len(modes_hz) + 0.4, 0.5 * (lo + hi), label, fontsize=8,
                color="#cc6677", va="center")
    ax.set_xlabel("Mode #")
    ax.set_ylabel("Natural frequency (Hz)")
    ax.set_title("Undamped torsional modes - washing-machine drive-train (3-DOF)")
    ax.set_xlim(0.4, len(modes_hz) + 2.2)
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def write_frf_plot(freqs_hz: np.ndarray, mag: np.ndarray, modes_hz: list[float],
                   out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 3.8))
    # log-y for FRF
    valid = np.isfinite(mag) & (mag > 0)
    ax.semilogy(freqs_hz[valid], mag[valid], color="#222", lw=1.4,
                label="|theta_drum / T_motor|")
    for f in modes_hz:
        if freqs_hz[0] <= f <= freqs_hz[-1]:
            ax.axvline(f, color="#4477aa", ls="--", lw=0.8, alpha=0.7)
    for label, (lo, hi) in SPIN_FREQS_HZ.items():
        ax.axvspan(lo, hi, alpha=0.12, color="#cc6677", lw=0)
        ax.text(0.5 * (lo + hi), ax.get_ylim()[1] * 0.5, label, fontsize=7,
                ha="center", color="#cc6677", rotation=90, va="center")
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Receptance magnitude (rad / N m, log)")
    ax.set_title("Torsional FRF - motor torque input -> drum angle output")
    ax.set_xlim(freqs_hz[0], freqs_hz[-1])
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def main() -> int:
    out_dir = Path("output/demo")
    out_dir.mkdir(parents=True, exist_ok=True)

    asm = build_assembly()
    modes = modal_frequencies(asm)

    print("=" * 60)
    print("Washing-machine drive-train torsional analysis (3-DOF)")
    print("=" * 60)
    print(f"Inertias [kg m^2]: motor={J_motor}, coupling={J_coup}, drum={J_drum}")
    print(f"Stiffness [Nm/rad]: shaft1={k_shaft1:.1f}, shaft2={k_shaft2:.1f}")
    print()
    print("Undamped natural frequencies:")
    for i, f in enumerate(modes, 1):
        print(f"  Mode {i}: {f:8.2f} Hz   ({2*np.pi*f:7.1f} rad/s)")
    print()

    hits = flag_resonance_in_spin_band(modes, tol_pct=10.0)
    if hits:
        print("WARNING - resonance proximity (mode within +/-10% of spin band):")
        for label, mode, dev in hits:
            print(f"  {label:<13s} band ~  mode {mode:.2f} Hz  ({dev:+.1f}%)")
    else:
        print("OK - no torsional mode within +/-10% of any operating spin band.")
    print()

    # FRF sweep
    f_axis = np.linspace(1.0, 300.0, 1500)
    mag = frf_magnitude(asm, f_axis)

    modal_png = out_dir / "drivetrain_modal.png"
    frf_png   = out_dir / "drivetrain_frf.png"
    write_modal_plot(modes, modal_png)
    write_frf_plot(f_axis, mag, modes, frf_png)

    print(f"Wrote {modal_png}")
    print(f"Wrote {frf_png}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
