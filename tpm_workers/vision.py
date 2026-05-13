"""
tpm_workers.vision - Phase 3 Day 2 Vision worker (scaffold, pre-internship)
ref: MASTER_PLAN_v6.md Section 6 + Section 25 (Mold & Die defect images)

Pipeline:
    image (jpg/png/pdf-page)
       │
       ▼  Tesseract OCR side-channel (if available - optional)
    text snippet from image
       │
       ▼  Qwen2.5-VL-3B (multimodal LLM via Ollama, ~2 GB VRAM)
    structured VisionAnalysis (description, defects, components)
       │
       ▼
    summary + JSON output file

Default VLM: Qwen2.5-VL-3B (per v6 spec - fits 8 GB VRAM with text orch).
Override via TPM_VISION_MODEL env var.

Degrades gracefully:
  - Tesseract not installed -> skip OCR, log a note (LLM still runs)
  - Qwen2.5-VL not pulled  -> return WorkerResult with clear "ollama pull
    qwen2.5-vl:3b" instruction; do NOT fall back to a text-only model.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from tpm_workers.base import WorkerInput, WorkerResult, WorkerStep, WorkerType

log = logging.getLogger(__name__)

DEFAULT_VISION_MODEL = os.getenv("TPM_VISION_MODEL", "qwen2.5-vl:3b")
SUPPORTED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}


# ============================================================
# Result schema
# ============================================================
class IdentifiedObject(BaseModel):
    name: str
    confidence: float = 0.0
    notes: str = ""


class VisionAnalysis(BaseModel):
    """Structured output from the vision worker."""
    image_path: str
    description: str = ""
    ocr_text: str = ""
    identified_objects: list[IdentifiedObject] = Field(default_factory=list)
    defects: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    raw_model_response: str = ""
    confidence: float = 0.0
    model_used: str = ""
    ocr_engine: str = ""           # 'tesseract' | 'skipped' | 'failed'


# ============================================================
# OCR side-channel (optional)
# ============================================================
def _run_ocr(image_path: Path) -> tuple[str, str]:
    """Returns (ocr_text, engine_status). engine_status is purely informational."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return "", "skipped: pytesseract or Pillow not installed"

    if not shutil.which("tesseract"):
        return "", "skipped: tesseract binary not on PATH"

    try:
        img = Image.open(image_path)
        # Try Thai + English; falls back to English if Thai data not installed
        try:
            text = pytesseract.image_to_string(img, lang="tha+eng")
        except pytesseract.TesseractError:
            text = pytesseract.image_to_string(img, lang="eng")
        return text.strip(), "tesseract"
    except Exception as e:  # noqa: BLE001
        return "", f"failed: {type(e).__name__}: {e}"


# ============================================================
# VLM call
# ============================================================
VISION_SYSTEM_PROMPT = """\
You are an industrial-maintenance assistant analyzing photos from a factory floor.
Focus on:
  - Defects (cracks, wear, sink marks, flash, burrs, corrosion, leakage)
  - Component identification (mold parts, dies, pumps, motors)
  - Visible measurement readings (gauges, displays)
  - Safety hazards (loose wires, fluid leaks, missing guards)

Respond in JSON with these keys:
  description: 1-2 sentences describing the image overall
  identified_objects: list of {name, confidence (0-1), notes}
  defects: list of strings (empty if none visible)
  suggested_actions: list of strings (empty if no action needed)
  confidence: overall 0-1 confidence in this analysis

Output VALID JSON ONLY. No prose.
"""


def _call_vision_model(
    image_path: Path,
    user_prompt: str,
    model: str,
    ocr_hint: str = "",
) -> tuple[dict, str]:
    """
    Returns (parsed_dict, raw_response_text).
    raw_response is returned even on parse failure so callers can display it.
    """
    import ollama

    # Read + base64-encode image (Ollama accepts bytes or base64)
    img_b64 = base64.b64encode(image_path.read_bytes()).decode("ascii")

    user_msg = user_prompt
    if ocr_hint:
        user_msg += f"\n\nText extracted by OCR from this image:\n---\n{ocr_hint[:1500]}\n---"

    response = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": VISION_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg, "images": [img_b64]},
        ],
        options={"temperature": 0.2},
        format="json",
    )
    raw = response["message"]["content"]
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        parsed = {}
    return parsed, raw


# ============================================================
# Worker entry point
# ============================================================
def _resolve_image_path(inp: WorkerInput) -> Optional[Path]:
    """Pick the image path from input.extras['image_path'] or target_subject."""
    candidate = inp.extras.get("image_path") or inp.target_subject
    if not candidate:
        return None
    p = Path(str(candidate))
    if not p.is_absolute():
        # Try relative to repo root
        p = (Path.cwd() / p).resolve()
    if not p.exists():
        return None
    if p.suffix.lower() not in SUPPORTED_IMAGE_EXTS:
        return None
    return p


def run_vision_worker(
    inp: WorkerInput,
    *,
    model: str = DEFAULT_VISION_MODEL,
) -> WorkerResult:
    """
    Analyze one image. Always returns a WorkerResult (never raises).
    """
    result = WorkerResult(worker_type=WorkerType.VISION)

    # ---- step 1: locate image ----
    step1 = WorkerStep(name="locate_image")
    img = _resolve_image_path(inp)
    if img is None:
        step1.finish(success=False,
                     error="no usable image path in inp.extras['image_path'] or target_subject")
        result.add_step(step1)
        result.summary = (
            "vision: no image to analyze. "
            "Pass extras={'image_path': '/path/to/image.jpg'} on the WorkerInput."
        )
        return result
    step1.output = {"image": str(img), "size_bytes": img.stat().st_size}
    step1.finish(success=True)
    result.add_step(step1)

    # ---- step 2: OCR (optional side-channel) ----
    step2 = WorkerStep(name="ocr")
    ocr_text, ocr_engine = _run_ocr(img)
    step2.output = {"engine": ocr_engine, "chars": len(ocr_text)}
    if not ocr_engine.startswith(("tesseract",)):
        step2.notes.append(ocr_engine)
    step2.finish(success=True)   # OCR is optional; never a hard fail
    result.add_step(step2)

    # ---- step 3: VLM analysis ----
    step3 = WorkerStep(name="vlm_analyze")
    parsed: dict = {}
    raw = ""
    try:
        parsed, raw = _call_vision_model(
            img,
            user_prompt=inp.user_request or "Describe this image and identify any defects.",
            model=model,
            ocr_hint=ocr_text,
        )
        step3.output = {"model": model, "chars": len(raw)}
        step3.finish(success=True)
    except Exception as e:  # noqa: BLE001
        msg = f"{type(e).__name__}: {e}"
        step3.finish(success=False, error=msg)
        # Provide friendly guidance for the common case
        if "not found" in str(e).lower() or "model" in str(e).lower():
            step3.notes.append(
                f"Hint: run `ollama pull {model}` to install the vision model."
            )
    result.add_step(step3)

    if not step3.success:
        result.summary = f"vision: VLM call failed - {step3.error}. " + " ".join(step3.notes)
        return result

    # ---- step 4: build VisionAnalysis + save JSON ----
    step4 = WorkerStep(name="serialize")
    objs = [IdentifiedObject(**o) if isinstance(o, dict) else IdentifiedObject(name=str(o))
            for o in (parsed.get("identified_objects") or [])]
    analysis = VisionAnalysis(
        image_path=str(img),
        description=parsed.get("description", "") or "",
        ocr_text=ocr_text,
        identified_objects=objs,
        defects=[str(x) for x in (parsed.get("defects") or [])],
        suggested_actions=[str(x) for x in (parsed.get("suggested_actions") or [])],
        raw_model_response=raw,
        confidence=float(parsed.get("confidence", 0.0) or 0.0),
        model_used=model,
        ocr_engine=ocr_engine,
    )
    out_dir = inp.output_dir if inp.output_dir else Path("output/vision")
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"vision_{img.stem}_{stamp}.json"
    out_path.write_text(
        json.dumps(analysis.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    step4.output = {"json": str(out_path)}
    step4.finish(success=True)
    result.add_step(step4)

    # ---- summary ----
    result.success = True
    result.confidence = analysis.confidence
    result.output_files = [str(out_path)]
    n_def = len(analysis.defects)
    n_obj = len(analysis.identified_objects)
    result.summary = (
        f"vision: model={model} OCR={ocr_engine.split(':')[0]} "
        f"objects={n_obj} defects={n_def} conf={analysis.confidence:.2f}"
    )
    result.metrics = {
        "n_objects": n_obj,
        "n_defects": n_def,
        "ocr_chars": len(ocr_text),
        "model": model,
        "ocr_engine": ocr_engine,
    }
    return result
