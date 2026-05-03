"""
benchmark_llm.py - measure tokens/sec + VRAM usage for an Ollama model
ref: MASTER_PLAN_v5.md § 3.3 (verify Flash Attention + KV cache q8_0 wins)

Usage:
    python scripts/benchmark_llm.py                       # default qwen3:8b
    python scripts/benchmark_llm.py --model tpm-orch
    python scripts/benchmark_llm.py --model qwen3:8b --runs 5
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import httpx  # noqa: E402

OLLAMA_HOST = "http://localhost:11434"

# Standard prompts to compare apples-to-apples
PROMPTS = [
    # Short Thai - intent-parser-like
    "ตอบสั้นๆ: ASTM A106 คืออะไร",
    # Medium English - synthesis-like
    "Summarize in 3 sentences: centrifugal pump cavitation symptoms and root causes.",
    # Longer mixed - report-writer-like
    (
        "Write a short maintenance summary in Thai for a SHIBAURA injection "
        "molding machine that had 12 events in the last 90 days, MTBF 175h, "
        "availability 97.5%. Include 3 bullet recommendations."
    ),
]


def vram_gb() -> float | None:
    try:
        import GPUtil  # type: ignore
        gpus = GPUtil.getGPUs()
        if not gpus:
            return None
        return float(gpus[0].memoryUsed) / 1024  # MB -> GB
    except Exception:
        return None


def env_snapshot() -> dict[str, str]:
    """Return Ollama-related env vars as seen by the running server."""
    # We can't read the server's env directly; show what we'd set on launch.
    import os
    return {
        "OLLAMA_FLASH_ATTENTION": os.getenv("OLLAMA_FLASH_ATTENTION", "(unset)"),
        "OLLAMA_KV_CACHE_TYPE": os.getenv("OLLAMA_KV_CACHE_TYPE", "(unset)"),
    }


def run_one(model: str, prompt: str, timeout: float = 240.0) -> dict:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.2},
    }
    t0 = time.perf_counter()
    with httpx.Client(timeout=timeout) as c:
        r = c.post(f"{OLLAMA_HOST}/api/chat", json=payload)
        r.raise_for_status()
        data = r.json()
    wall_ms = int((time.perf_counter() - t0) * 1000)

    # Ollama returns these fields in the response
    eval_count = data.get("eval_count", 0)               # output tokens
    eval_duration = data.get("eval_duration", 0)         # ns
    prompt_eval_count = data.get("prompt_eval_count", 0)
    prompt_eval_duration = data.get("prompt_eval_duration", 0)

    decode_tps = (
        eval_count / (eval_duration / 1e9) if eval_duration > 0 else 0
    )
    prefill_tps = (
        prompt_eval_count / (prompt_eval_duration / 1e9)
        if prompt_eval_duration > 0 else 0
    )
    return {
        "wall_ms": wall_ms,
        "input_tokens": prompt_eval_count,
        "output_tokens": eval_count,
        "decode_tok_per_sec": round(decode_tps, 1),
        "prefill_tok_per_sec": round(prefill_tps, 1),
        "response_chars": len(data.get("message", {}).get("content", "")),
    }


def warmup(model: str) -> None:
    """First call loads the model into VRAM - don't count it."""
    print(f"[warmup] {model} ...", end="", flush=True)
    t0 = time.perf_counter()
    try:
        run_one(model, "say hi", timeout=300.0)
        print(f" {int((time.perf_counter() - t0) * 1000)}ms")
    except Exception as e:  # noqa: BLE001
        print(f" FAIL: {e}")


def main() -> int:
    p = argparse.ArgumentParser(description="Benchmark Ollama model speed")
    p.add_argument("--model", default="qwen3:8b")
    p.add_argument("--runs", type=int, default=3, help="runs per prompt")
    p.add_argument("--json", action="store_true", help="output raw JSON only")
    args = p.parse_args()

    print("=" * 64)
    print(f"TPM AI - LLM benchmark: {args.model}")
    print("=" * 64)
    print(f"Env on this side: {env_snapshot()}")
    print(f"VRAM before: {vram_gb()} GB")
    print()

    warmup(args.model)
    print(f"VRAM after model load: {vram_gb()} GB")
    print()

    all_results: dict[str, list[dict]] = {}
    for i, prompt in enumerate(PROMPTS, 1):
        print(f"[prompt {i}/{len(PROMPTS)}] {prompt[:60]}{'...' if len(prompt)>60 else ''}")
        runs = []
        for run_i in range(args.runs):
            try:
                r = run_one(args.model, prompt)
                runs.append(r)
                print(f"  run {run_i+1}: "
                      f"in={r['input_tokens']} out={r['output_tokens']} "
                      f"decode={r['decode_tok_per_sec']} tok/s "
                      f"prefill={r['prefill_tok_per_sec']} tok/s "
                      f"wall={r['wall_ms']}ms")
            except Exception as e:  # noqa: BLE001
                print(f"  run {run_i+1}: FAIL: {e}")
        all_results[f"prompt_{i}"] = runs

    # Summary
    decode_vals = [r["decode_tok_per_sec"]
                   for runs in all_results.values() for r in runs
                   if r.get("decode_tok_per_sec", 0) > 0]
    prefill_vals = [r["prefill_tok_per_sec"]
                    for runs in all_results.values() for r in runs
                    if r.get("prefill_tok_per_sec", 0) > 0]
    print()
    print("=" * 64)
    print("Summary (across all runs)")
    print("=" * 64)
    if decode_vals:
        print(f"  decode tok/s   median={statistics.median(decode_vals):.1f}  "
              f"min={min(decode_vals):.1f}  max={max(decode_vals):.1f}")
    if prefill_vals:
        print(f"  prefill tok/s  median={statistics.median(prefill_vals):.1f}  "
              f"min={min(prefill_vals):.1f}  max={max(prefill_vals):.1f}")
    print(f"  VRAM final:    {vram_gb()} GB")

    if args.json:
        print()
        print(json.dumps({
            "model": args.model,
            "env": env_snapshot(),
            "vram_gb_final": vram_gb(),
            "results": all_results,
            "summary_decode_median": statistics.median(decode_vals) if decode_vals else None,
            "summary_prefill_median": statistics.median(prefill_vals) if prefill_vals else None,
        }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
