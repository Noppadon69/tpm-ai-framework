"""
tests/test_vision_worker.py - unit tests for tpm_workers.vision

No Ollama or Tesseract installation required - we monkey-patch the
network/OCR calls and verify the worker's control flow, serialization,
and error handling.

Run:
    .venv/Scripts/python.exe tests/test_vision_worker.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

import tpm_workers.vision as vw  # noqa: E402
from tpm_workers.base import WorkerInput, WorkerType  # noqa: E402

PASS = "[PASS]"
FAIL = "[FAIL]"
_failures: list[str] = []


def check(name: str, cond: bool, detail: str = ""):
    if cond:
        print(f"{PASS} {name}")
    else:
        print(f"{FAIL} {name}  {detail}")
        _failures.append(name)


def _mk_fake_png(tmpdir: Path) -> Path:
    """Write a tiny valid PNG so Path checks pass; content irrelevant for these tests."""
    # 1x1 transparent PNG
    png_bytes = bytes.fromhex(
        "89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C489"
        "0000000D49444154789C636200010000050001"
        "5A4D60E50000000049454E44AE426082"
    )
    p = tmpdir / "fake.png"
    p.write_bytes(png_bytes)
    return p


def t_no_image_path():
    inp = WorkerInput(
        worker_type=WorkerType.VISION,
        session_id="t",
        user_request="describe",
        target_subject="",
    )
    r = vw.run_vision_worker(inp)
    check("no-img: not successful", not r.success)
    check("no-img: summary mentions image", "image" in r.summary.lower())
    check("no-img: step locate_image failed",
          any(s.name == "locate_image" and not s.success for s in r.steps))


def t_image_not_found():
    inp = WorkerInput(
        worker_type=WorkerType.VISION, session_id="t",
        user_request="describe", target_subject="",
        extras={"image_path": "/does/not/exist.jpg"},
    )
    r = vw.run_vision_worker(inp)
    check("missing-img: not successful", not r.success)


def t_full_happy_path():
    """Image exists, OCR + VLM both succeed via monkey-patching."""
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        img = _mk_fake_png(td_path)

        # Patch OCR + VLM
        orig_ocr = vw._run_ocr
        orig_vlm = vw._call_vision_model
        vw._run_ocr = lambda p: ("READING: 245C", "tesseract")
        vw._call_vision_model = lambda p, user_prompt, model, ocr_hint="": (
            {
                "description": "Test image of a gauge showing high temperature.",
                "identified_objects": [{"name": "gauge", "confidence": 0.9, "notes": "analog"}],
                "defects": ["overheat reading"],
                "suggested_actions": ["check coolant"],
                "confidence": 0.8,
            },
            '{"description": "..."}',
        )
        try:
            inp = WorkerInput(
                worker_type=WorkerType.VISION, session_id="t",
                user_request="what is wrong",
                target_subject="",
                output_dir=td_path / "out",
                extras={"image_path": str(img)},
            )
            r = vw.run_vision_worker(inp)
            check("happy: success=True", r.success)
            check("happy: confidence > 0", r.confidence > 0)
            check("happy: output JSON written",
                  len(r.output_files) == 1 and Path(r.output_files[0]).exists())
            # Inspect saved JSON
            saved = json.loads(Path(r.output_files[0]).read_text(encoding="utf-8"))
            check("happy: saved has description", "gauge" in saved["description"].lower())
            check("happy: saved has defects", saved["defects"] == ["overheat reading"])
            check("happy: ocr_text persisted", "245C" in saved["ocr_text"])
            check("happy: model_used recorded", saved["model_used"])
            check("happy: ocr_engine=tesseract", saved["ocr_engine"] == "tesseract")
            check("happy: metrics populated",
                  r.metrics.get("n_objects") == 1 and r.metrics.get("n_defects") == 1)
        finally:
            vw._run_ocr = orig_ocr
            vw._call_vision_model = orig_vlm


def t_vlm_failure_friendly_message():
    """When VLM raises (e.g. model not pulled), we get a helpful summary."""
    with tempfile.TemporaryDirectory() as td:
        img = _mk_fake_png(Path(td))
        orig_ocr = vw._run_ocr
        orig_vlm = vw._call_vision_model
        vw._run_ocr = lambda p: ("", "skipped")

        def fake_call(*a, **kw):
            raise RuntimeError("model 'qwen2.5-vl:3b' not found")

        vw._call_vision_model = fake_call
        try:
            inp = WorkerInput(
                worker_type=WorkerType.VISION, session_id="t",
                user_request="?", target_subject="",
                output_dir=Path(td) / "out",
                extras={"image_path": str(img)},
            )
            r = vw.run_vision_worker(inp)
            check("vlm-fail: not successful", not r.success)
            check("vlm-fail: summary contains hint",
                  "ollama pull" in r.summary)
            check("vlm-fail: vlm_analyze step failed",
                  any(s.name == "vlm_analyze" and not s.success for s in r.steps))
        finally:
            vw._run_ocr = orig_ocr
            vw._call_vision_model = orig_vlm


def t_unsupported_extension():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "not_an_image.exe"
        p.write_bytes(b"fake")
        inp = WorkerInput(
            worker_type=WorkerType.VISION, session_id="t",
            user_request="?", target_subject="",
            extras={"image_path": str(p)},
        )
        r = vw.run_vision_worker(inp)
        check("unsupported: rejected", not r.success)


def main() -> int:
    for fn in (
        t_no_image_path,
        t_image_not_found,
        t_full_happy_path,
        t_vlm_failure_friendly_message,
        t_unsupported_extension,
    ):
        print(f"\n--- {fn.__name__} ---")
        fn()
    print()
    if _failures:
        print(f"{FAIL} {len(_failures)} test(s) failed")
        return 1
    print(f"{PASS} all tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
