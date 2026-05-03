"""
setup_models.py - one-shot creator for TPM AI custom Ollama models
ref: MASTER_PLAN_v5.md § 3.3 + § 4.2

Reads Modelfile in models/<role>/ and runs `ollama create`.
Idempotent - safe to re-run.

Usage:
    python scripts/setup_models.py             # create all
    python scripts/setup_models.py --only orch # create only tpm-orch
    python scripts/setup_models.py --force     # remove + recreate
"""
from __future__ import annotations

import argparse
import logging
import shutil
import subprocess
import sys
from pathlib import Path

# UTF-8 stdout
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

REPO = Path(__file__).resolve().parent.parent

# Map of role -> (ollama tag, Modelfile path)
MODELS = {
    "orch": ("tpm-orch:latest", REPO / "models" / "orchestrator" / "Modelfile"),
    "scavenger": ("tpm-scavenger:latest", REPO / "models" / "scavenger" / "Modelfile"),
}


def has_ollama() -> bool:
    return shutil.which("ollama") is not None


def model_exists(tag: str) -> bool:
    try:
        out = subprocess.check_output(
            ["ollama", "list"], text=True, stderr=subprocess.STDOUT, timeout=10
        )
        # tag like "tpm-orch:latest" - check for "tpm-orch" presence
        return tag.split(":")[0] in out
    except subprocess.SubprocessError:
        return False


def create_model(tag: str, modelfile: Path, force: bool = False) -> bool:
    if not modelfile.exists():
        print(f"[FAIL] Modelfile missing: {modelfile}")
        return False
    if model_exists(tag) and not force:
        print(f"[skip] {tag} already exists (use --force to recreate)")
        return True
    if force and model_exists(tag):
        print(f"[force] removing existing {tag}")
        subprocess.run(["ollama", "rm", tag], check=False)

    print(f"[create] {tag} from {modelfile.relative_to(REPO)} ...")
    res = subprocess.run(
        ["ollama", "create", tag, "-f", str(modelfile)],
        text=True,
    )
    if res.returncode != 0:
        print(f"[FAIL] ollama create returned {res.returncode}")
        return False
    print(f"[ok] created {tag}")
    return True


def main() -> int:
    p = argparse.ArgumentParser(description="Create TPM AI custom Ollama models")
    p.add_argument("--only", choices=sorted(MODELS), help="create only one role")
    p.add_argument("--force", action="store_true", help="remove + recreate")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not has_ollama():
        print("[FAIL] ollama not in PATH - install from ollama.com")
        return 2

    targets = [args.only] if args.only else list(MODELS)

    print("=" * 64)
    print("TPM AI - Custom model setup")
    print("=" * 64)

    n_ok = 0
    n_fail = 0
    for role in targets:
        tag, modelfile = MODELS[role]
        if create_model(tag, modelfile, force=args.force):
            n_ok += 1
        else:
            n_fail += 1

    print()
    print("=" * 64)
    print(f"Summary: ok={n_ok}  fail={n_fail}")
    if n_ok and not n_fail:
        print()
        print("Next:")
        print('  Add to .env:  TPM_ORCHESTRATOR_MODEL=tpm-orch:latest')
        print("  Test:         ollama run tpm-orch \"hello\"")
    print("=" * 64)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
