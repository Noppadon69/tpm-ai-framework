#!/usr/bin/env python
"""
scripts/lookup_defect.py - CLI helper for the Toshiba intern (Section 25).

Quick reference: given a mold defect, show the catalog of probable causes.
Optional process-param + material flags trigger the deterministic
MoldAnalyseNode for a deviation-aware ranking.

Examples:
    # Bare lookup
    python scripts/lookup_defect.py "Flash"
    python scripts/lookup_defect.py "รอยบุ๋ม"

    # With process data + material
    python scripts/lookup_defect.py "Sink mark" \
        --param holding_pressure=20 --param barrel_temperature=200 \
        --material P20 --shot-count 25000

    # List supported defects
    python scripts/lookup_defect.py --list

ASCII-only output for Windows CMD (cp1252).
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# UTF-8 for Thai input/output
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from tpm_mold import DEFECT_CATALOG, analyse, causes_for  # noqa: E402


def _parse_param(text: str) -> tuple[str, float]:
    """Parse 'name=value' -> (name, float(value))."""
    if "=" not in text:
        raise argparse.ArgumentTypeError(f"expected 'name=value', got {text!r}")
    name, value_s = text.split("=", 1)
    return name.strip(), float(value_s.strip())


def main() -> int:
    p = argparse.ArgumentParser(
        description="Lookup mold/die defect causes (Section 25).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="ASCII-only output. Thai aliases accepted for defect names.",
    )
    p.add_argument("defect", nargs="?", help="defect name (English, Thai alias, or enum value)")
    p.add_argument(
        "--param", "-p", action="append", default=[],
        type=_parse_param, metavar="name=value",
        help="process param measurement (repeatable). "
             "Names from tpm_mold.process_spec.PROCESS_SPECS.",
    )
    p.add_argument("--material", "-m", help="mold material (SKD61, P20, NAK80, SKD11, S50C)")
    p.add_argument("--shot-count", "-s", type=int, help="cumulative shot/stroke count")
    p.add_argument("--list", action="store_true", help="list supported defects + materials")

    args = p.parse_args()

    if args.list:
        print("Supported defects (Section 25.2.2):")
        for d in sorted(DEFECT_CATALOG):
            n_causes = len(DEFECT_CATALOG[d])
            print(f"  {d:14s} ({n_causes} causes)")
        print()
        print("Supported materials (Section 25.2.3):")
        from tpm_mold import MATERIALS
        for name, m in sorted(MATERIALS.items()):
            print(f"  {name:6s}  {m.family:18s}  {m.typical_application}")
        return 0

    if not args.defect:
        p.error("defect argument required (or pass --list)")

    if not args.param and not args.material:
        # Simple lookup
        causes = causes_for(args.defect)
        if not causes:
            print(f"[FAIL] unknown defect: {args.defect!r}")
            print("Run with --list to see supported defects.")
            return 2
        print(f"Defect: {args.defect}")
        print(f"Causes ({len(causes)}):")
        for i, c in enumerate(causes, 1):
            print(f"  {i}. [{c.category}, priority={c.priority}] {c.description}")
            print(f"     -> check via: {c.check_via}")
        return 0

    # Full deterministic analyse
    process_log = dict(args.param) if args.param else None
    diag = analyse(
        defect=args.defect,
        process_log=process_log,
        mold_material=args.material,
        shot_count=args.shot_count,
    )
    print(diag.summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
