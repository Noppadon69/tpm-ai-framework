"""
setup_searxng.py — generate settings.yml from template (one-shot)
ref: MASTER_PLAN_v5.md § 6.4.1

Usage:
  python scripts/setup_searxng.py            # generate if missing
  python scripts/setup_searxng.py --force    # overwrite
"""
from __future__ import annotations

import argparse
import secrets
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = REPO_ROOT / "services" / "searxng" / "settings.yml.example"
TARGET = REPO_ROOT / "services" / "searxng" / "settings.yml"


def main() -> int:
    p = argparse.ArgumentParser(description="Generate SearXNG settings.yml")
    p.add_argument("--force", action="store_true", help="overwrite existing")
    args = p.parse_args()

    if not TEMPLATE.exists():
        print(f"[FAIL] template missing: {TEMPLATE}", file=sys.stderr)
        return 2

    if TARGET.exists() and not args.force:
        print(f"[skip] {TARGET} already exists (use --force to overwrite)")
        return 0

    template = TEMPLATE.read_text(encoding="utf-8")
    secret = secrets.token_hex(32)
    rendered = template.replace("SECRET_KEY_PLACEHOLDER", secret)
    TARGET.write_text(rendered, encoding="utf-8")
    print(f"[ok] wrote {TARGET} with fresh secret_key")
    print()
    print("Next steps:")
    print("  cd services/searxng")
    print("  docker compose up -d")
    print("  curl 'http://localhost:8888/search?q=test&format=json'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
