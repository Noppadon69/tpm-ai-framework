#!/usr/bin/env python
"""
scripts/ingest_doc.py - add files into the ChromaDB tpm_wiki collection.
ref: MASTER_PLAN_v6.md Phase 1 Day 1-3

Examples:
    # Add one file
    python scripts/ingest_doc.py raw_data/_dummy/DUMMY_LOTO_Procedures.md

    # Bulk add a directory (recursive, all supported extensions)
    python scripts/ingest_doc.py --dir raw_data/

    # List ingested docs
    python scripts/ingest_doc.py --list

    # Quick query of the wiki
    python scripts/ingest_doc.py --search "LOTO procedure boiler"

Mark a doc CONFIDENTIAL so L3 egress won't accidentally web-search subjects
that came from it:
    python scripts/ingest_doc.py path/to/internal.md --classification CONFIDENTIAL
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

from tpm_knowledge import (  # noqa: E402
    ingest_file,
    list_documents,
    search_chunks,
)

SUPPORTED_EXTS = {".pdf", ".docx", ".xlsx", ".pptx", ".md", ".markdown",
                  ".txt", ".html", ".htm"}


def main() -> int:
    p = argparse.ArgumentParser(description="Ingest docs into the tpm_wiki ChromaDB collection.")
    p.add_argument("path", nargs="?", help="file to ingest (or query string with --search)")
    p.add_argument("--dir", help="directory to ingest recursively (instead of single file)")
    p.add_argument("--classification", default="INTERNAL",
                   choices=["PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"],
                   help="data classification for egress gate (default: INTERNAL)")
    p.add_argument("--list", action="store_true", help="list ingested docs and exit")
    p.add_argument("--search", action="store_true",
                   help="treat `path` as a query string; print top-5 chunks")
    args = p.parse_args()

    if args.list:
        docs = list_documents()
        if not docs:
            print("(no documents ingested yet)")
            return 0
        print(f"Wiki contains {len(docs)} documents:")
        for d in docs:
            print(f"  [{d['classification']}] {d['filename']:40s} "
                  f"chunks={d['n_chunks']:3d}  title={d['title'][:40]!r}")
        return 0

    if args.search:
        if not args.path:
            p.error("--search needs a query string")
        hits = search_chunks(args.path, k=5)
        if not hits:
            print(f"(no hits for {args.path!r})")
            return 0
        print(f"Top {len(hits)} chunks for {args.path!r}:")
        for i, h in enumerate(hits, 1):
            print(f"\n  [{i}] score={h.score:.3f}  {h.filename} #{h.chunk_idx} "
                  f"({h.classification})")
            print(f"      title: {h.title}")
            preview = h.chunk_text.replace("\n", " ")[:200]
            print(f"      preview: {preview}{'...' if len(h.chunk_text) > 200 else ''}")
        return 0

    if args.dir:
        root = Path(args.dir)
        if not root.exists() or not root.is_dir():
            print(f"[FAIL] not a directory: {root}")
            return 2
        files = [f for f in root.rglob("*")
                 if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS]
        if not files:
            print(f"(no supported files under {root})")
            return 0
        print(f"Ingesting {len(files)} files from {root}...")
        ok = 0
        for f in files:
            t0 = time.perf_counter()
            try:
                r = ingest_file(f, classification=args.classification)
                dt = time.perf_counter() - t0
                status = "OK" if r.ok else f"SKIP ({r.skipped_reason})"
                print(f"  [{status}] {f.relative_to(root)} chunks={r.n_chunks} "
                      f"chars={r.chunk_chars_total} t={dt:.1f}s")
                if r.ok:
                    ok += 1
            except Exception as e:  # noqa: BLE001
                print(f"  [FAIL] {f.relative_to(root)}: {e}")
        print(f"\n{ok}/{len(files)} ingested.")
        return 0 if ok == len(files) else 1

    if not args.path:
        p.error("path required (file to ingest), or use --dir / --list / --search")

    t0 = time.perf_counter()
    r = ingest_file(args.path, classification=args.classification)
    dt = time.perf_counter() - t0
    if not r.ok:
        print(f"[SKIP] {args.path}: {r.skipped_reason}")
        return 1
    print(f"[OK] ingested {args.path}")
    print(f"     chunks: {r.n_chunks}")
    print(f"     chars:  {r.chunk_chars_total}")
    print(f"     class:  {r.classification}")
    print(f"     time:   {dt:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
