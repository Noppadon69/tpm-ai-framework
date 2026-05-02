"""
cli_demo.py - interactive CLI demo of Phase 2 orchestrator
ref: MASTER_PLAN_v5.md § 22.4 (Phase 2 acceptance)

Run:
    .venv/Scripts/python.exe scripts/cli_demo.py
    .venv/Scripts/python.exe scripts/cli_demo.py "ราคา bearing SKF 6205 ล่าสุด"

Type 'exit' or Ctrl-C to quit.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

# Force UTF-8 stdout/stderr (Windows CMD defaults to cp1252 which can't print Thai)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

# Load .env
env_file = REPO / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from tpm_core.llm import health  # noqa: E402
from tpm_core.orchestrator import StdinUI, run_orchestrator  # noqa: E402


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    # Quiet noisy libs
    for noisy in ("httpx", "httpcore", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    if not health():
        print("[FAIL] Ollama not reachable. Run: ollama serve")
        return 2

    print("=" * 64)
    print("TPM AI - CLI Demo (Phase 2: clarification + L3 search)")
    print("=" * 64)
    print("Tips:")
    print("  - phrase clearly  -> AI confirms then proceeds")
    print("  - phrase vaguely  -> AI asks A/B/C clarification")
    print("  - 'ทำไปเลย' / 'go ahead' -> skip clarification")
    print("  - 'exit' or Ctrl-C to quit")
    print()

    # Single-shot mode if arg passed
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
        run_one(prompt)
        return 0

    # Interactive loop
    while True:
        try:
            prompt = input("\n>>> Your request: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            return 0
        if not prompt:
            continue
        if prompt.lower() in ("exit", "quit"):
            return 0
        run_one(prompt)


def run_one(prompt: str) -> None:
    print()
    print(f">>> Processing: {prompt!r}")
    print("-" * 64)
    final = run_orchestrator(prompt, ui=StdinUI())
    print()
    print("=" * 64)
    print(f"Phase: {final.phase.value}")
    if final.error:
        print(f"Error: {final.error}")
    if final.intent:
        print(f"Intent: {final.intent.action} | {final.intent.subject} | "
              f"conf={final.intent.confidence:.2f}")
    if final.recon_results:
        print(f"Recon:  provider={final.recon_results.get('provider')} "
              f"results={final.recon_results.get('n_results')}")
    print(f"Handoff log: {len(final.handoff_log)} packets")
    print("=" * 64)


if __name__ == "__main__":
    raise SystemExit(main())
