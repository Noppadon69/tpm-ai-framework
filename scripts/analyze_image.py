#!/usr/bin/env python
"""
scripts/analyze_image.py - one-shot Vision worker invocation
ref: MASTER_PLAN_v6.md Phase 3 Day 2 (vision scaffold)

Usage:
    python scripts/analyze_image.py path/to/photo.jpg
    python scripts/analyze_image.py path/to/photo.jpg --prompt "What defect is this?"
    python scripts/analyze_image.py path/to/photo.jpg --model qwen2.5-vl:7b

Setup (one-time):
    1. ollama pull qwen2.5-vl:3b      # ~2 GB, fits 8 GB VRAM with text orch
    2. pip install pytesseract        # optional OCR side-channel
    3. install tesseract binary       # https://github.com/UB-Mannheim/tesseract/wiki

Output: JSON written to output/vision/vision_<stem>_<timestamp>.json
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

from tpm_workers.base import WorkerInput, WorkerType  # noqa: E402
from tpm_workers.vision import DEFAULT_VISION_MODEL, run_vision_worker  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Run the Vision worker on a single image.")
    p.add_argument("image", help="path to image file (jpg/png/webp/...)")
    p.add_argument("--prompt", default="Describe this image and identify any defects.",
                   help="user prompt for the VLM")
    p.add_argument("--model", default=DEFAULT_VISION_MODEL,
                   help=f"vision model (default {DEFAULT_VISION_MODEL})")
    p.add_argument("--output-dir", default="output/vision",
                   help="where to write JSON output")
    args = p.parse_args()

    img = Path(args.image)
    if not img.exists():
        print(f"[FAIL] image not found: {img}")
        return 2

    inp = WorkerInput(
        worker_type=WorkerType.VISION,
        session_id="cli",
        user_request=args.prompt,
        target_subject=str(img),
        output_dir=Path(args.output_dir),
        extras={"image_path": str(img)},
    )

    result = run_vision_worker(inp, model=args.model)
    print()
    print(f"[{result.worker_type.value} worker] {result.summary}")
    for s in result.steps:
        notes = "; ".join(s.notes) if s.notes else "-"
        print(f"  [{s.name:14s}] success={s.success}  {notes}")
        if not s.success and s.error:
            print(f"      error: {s.error}")
    for f in result.output_files:
        print(f"  -> {f}")
    if result.metrics:
        print(f"  metrics: {result.metrics}")
    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
