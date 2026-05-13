"""
test_vibration_worker.py - run_vibration_worker smoke tests.

Generates a synthetic accelerometer CSV with a known BPFO fault signature
and verifies the worker pipeline:
  - validates inputs (csv_path, f_r_hz, bearing preset)
  - loads + computes spectra (raw + envelope)
  - classifies fault verdict against bearing geometry
  - writes audit .md

No LLM, no network, no SSL. Safe under Bug #7.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
for _m in [k for k in list(sys.modules) if k == "tpm_workers" or k.startswith("tpm_workers.")]:
    del sys.modules[_m]

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from tpm_workers.base import WorkerInput, WorkerType  # noqa: E402
from tpm_workers import vibration  # noqa: E402

assert str(REPO_ROOT) in vibration.__file__, (
    f"loaded wrong vibration.py: {vibration.__file__}"
)

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"[PASS] {name}{(' - ' + detail) if detail else ''}")
    else:
        FAIL += 1
        print(f"[FAIL] {name}  {detail}")


# --------------------------------------------------------------------------
# Synthetic data builder (compact version of demo_vibration.py logic)
# --------------------------------------------------------------------------
def make_csv_with_bpfo(path: Path, *, f_r: float = 24.0, fs: float = 8000.0,
                      duration: float = 2.0) -> None:
    rng = np.random.default_rng(7)
    t = np.arange(0.0, duration, 1.0 / fs)
    n = 8
    d = 7.94
    D = 33.5
    bpfo = (n / 2.0) * f_r * (1.0 - d / D)

    a = 0.30 * np.sin(2.0 * np.pi * f_r * t)
    for k in range(int(duration * bpfo) + 1):
        t0 = (k + 0.5) / bpfo
        dt = t - t0
        mask = dt >= 0.0
        ring = np.exp(-800.0 * dt[mask]) * np.sin(2.0 * np.pi * 3000.0 * dt[mask])
        a[mask] += 0.55 * ring
    a += 0.05 * rng.standard_normal(t.size)
    pd.DataFrame({"time_s": t, "accel_g": a}).to_csv(path, index=False)


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------
def t_bearing_fault_freq_math() -> None:
    """Theoretical BPFO for 6204 @ 24 Hz should be ~73.25 Hz."""
    ff = vibration.bearing_fault_freqs(vibration.BEARING_PRESETS["6204"], 24.0)
    check("math: BPFO ~73.25", abs(ff["BPFO"] - 73.25) < 0.5,
          detail=f"got {ff['BPFO']:.2f}")
    check("math: BPFI ~118.75", abs(ff["BPFI"] - 118.75) < 0.5)
    check("math: FTF ~9.16",   abs(ff["FTF"] - 9.16) < 0.2)


def t_missing_inputs() -> None:
    inp = WorkerInput(worker_type=WorkerType.VIBRATION, session_id="t1",
                      user_request="", extras={})
    r = vibration.run_vibration_worker(inp)
    check("missing-csv: success False", r.success is False)
    check("missing-csv: step1 errored", r.steps and r.steps[0].error)


def t_unknown_bearing_preset() -> None:
    with tempfile.TemporaryDirectory() as td:
        csv = Path(td) / "x.csv"
        make_csv_with_bpfo(csv)
        inp = WorkerInput(
            worker_type=WorkerType.VIBRATION, session_id="t2",
            user_request="", output_dir=Path(td),
            extras={"accel_csv": str(csv), "f_r_hz": 24.0, "bearing": "9999XX"},
        )
        r = vibration.run_vibration_worker(inp)
        check("bad-bearing: rejected", r.success is False)
        check("bad-bearing: error mentions preset",
              "preset" in (r.steps[0].error if r.steps else "").lower()
              or "unknown" in (r.steps[0].error if r.steps else "").lower())


def t_happy_path_outer_race() -> None:
    """End-to-end: synthetic BPFO trace -> outer_race verdict."""
    with tempfile.TemporaryDirectory() as td:
        csv = Path(td) / "drum_24Hz.csv"
        make_csv_with_bpfo(csv, f_r=24.0, duration=2.0)
        inp = WorkerInput(
            worker_type=WorkerType.VIBRATION, session_id="happy",
            user_request="ตรวจสภาพ bearing drum", output_dir=Path(td),
            extras={"accel_csv": str(csv), "f_r_hz": 24.0, "bearing": "6204"},
        )
        r = vibration.run_vibration_worker(inp)

        check("happy: success True", r.success is True,
              detail=f"summary={r.summary}")
        check("happy: 4 steps + all OK",
              len(r.steps) == 4 and all(s.success for s in r.steps),
              detail=f"steps={[s.name for s in r.steps]}")
        verdict = r.metrics.get("fault_verdict")
        check("happy: verdict = outer_race",
              verdict == "outer_race", detail=f"got {verdict}")
        err_matched = r.metrics.get("envelope_peak_error_vs_matched_pct")
        check("happy: envelope error vs matched harmonic < 2%",
              err_matched is not None and err_matched < 2.0,
              detail=f"got {err_matched:.2f}%" if err_matched is not None else "None")
        check("happy: confidence >= 0.80 (allow harmonic penalty)",
              r.confidence >= 0.80, detail=f"got {r.confidence}")
        check("happy: matched_harmonic in {1,2,3}",
              r.metrics.get("matched_harmonic") in {1, 2, 3})
        check("happy: audit .md written",
              len(r.output_files) == 1 and Path(r.output_files[0]).is_file(),
              detail=str(r.output_files))


def t_audit_content() -> None:
    with tempfile.TemporaryDirectory() as td:
        csv = Path(td) / "audit.csv"
        make_csv_with_bpfo(csv, f_r=24.0, duration=2.0)
        inp = WorkerInput(
            worker_type=WorkerType.VIBRATION, session_id="audit",
            user_request="", output_dir=Path(td),
            extras={"accel_csv": str(csv), "f_r_hz": 24.0, "bearing": "6204"},
        )
        r = vibration.run_vibration_worker(inp)
        if not r.output_files:
            check("audit: file missing", False, "no output_files")
            return
        text = Path(r.output_files[0]).read_text(encoding="utf-8")
        check("audit: mentions BPFO",     "BPFO" in text)
        check("audit: mentions verdict",  "outer_race" in text)
        check("audit: mentions bearing",  "6204" in text)
        check("audit: mentions f_r",      "24.00 Hz" in text or "24.0 Hz" in text)


def t_custom_bearing_dict() -> None:
    """Pass bearing as dict instead of preset string."""
    with tempfile.TemporaryDirectory() as td:
        csv = Path(td) / "custom.csv"
        make_csv_with_bpfo(csv)
        custom = {"n_balls": 8, "ball_diam_mm": 7.94, "pitch_diam_mm": 33.5,
                  "angle_deg": 0.0}
        inp = WorkerInput(
            worker_type=WorkerType.VIBRATION, session_id="custom",
            user_request="", output_dir=Path(td),
            extras={"accel_csv": str(csv), "f_r_hz": 24.0, "bearing": custom},
        )
        r = vibration.run_vibration_worker(inp)
        check("custom-geom: success", r.success is True)
        check("custom-geom: verdict outer_race",
              r.metrics.get("fault_verdict") == "outer_race")


def main() -> int:
    print("=" * 60)
    print("Vibration worker smoke tests")
    print("=" * 60)
    t_bearing_fault_freq_math()
    t_missing_inputs()
    t_unknown_bearing_preset()
    t_happy_path_outer_race()
    t_audit_content()
    t_custom_bearing_dict()

    print("-" * 60)
    if FAIL == 0:
        print(f"[PASS] all tests passed  ({PASS} assertions)")
        return 0
    print(f"[FAIL] {FAIL} failed / {PASS} passed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
