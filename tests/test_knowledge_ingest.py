"""
tests/test_knowledge_ingest.py - unit tests for tpm_knowledge.ingest
(no Ollama / no Chroma; only the deterministic pieces)

Run:
    .venv/Scripts/python.exe tests/test_knowledge_ingest.py
"""
from __future__ import annotations

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

from tpm_knowledge.ingest import (  # noqa: E402
    _doc_id_prefix,
    _extract_title,
    chunk_text,
    convert_to_markdown,
)

PASS = "[PASS]"
FAIL = "[FAIL]"
_failures: list[str] = []


def check(name: str, cond: bool, detail: str = ""):
    if cond:
        print(f"{PASS} {name}")
    else:
        print(f"{FAIL} {name}  {detail}")
        _failures.append(name)


def t_convert_markdown_passthrough():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as tf:
        tf.write("# Title\n\nBody text.")
        p = Path(tf.name)
    try:
        text = convert_to_markdown(p)
        check("conv: md passthrough preserves text", "Body text." in text)
        check("conv: md passthrough preserves header", "# Title" in text)
    finally:
        p.unlink(missing_ok=True)


def t_convert_txt_passthrough():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as tf:
        tf.write("plain text content here")
        p = Path(tf.name)
    try:
        text = convert_to_markdown(p)
        check("conv: txt passthrough", "plain text content" in text)
    finally:
        p.unlink(missing_ok=True)


def t_chunk_text():
    # Long enough to require splitting (chunk_size=512 tokens; ~2000+ chars)
    text = ("Section 1. " + "blah " * 200 + "\n\n"
            "Section 2. " + "blah " * 200 + "\n\n"
            "Section 3. " + "blah " * 200)
    chunks = chunk_text(text)
    check("chunk: returns >= 1 chunk", len(chunks) >= 1)
    check("chunk: all chunks are strings", all(isinstance(c, str) for c in chunks))
    check("chunk: total chars >= original (modulo whitespace)",
          sum(len(c) for c in chunks) >= len(text) * 0.8)


def t_chunk_short_text():
    chunks = chunk_text("brief content")
    check("chunk: short text yields >= 1 chunk", len(chunks) >= 1)


def t_extract_title():
    text = "# Equipment Specifications\n\nbody"
    check("title: from first h1", _extract_title(text, "fallback") == "Equipment Specifications")

    text2 = "no header here\nstill no header"
    check("title: fallback used when no header",
          _extract_title(text2, "FALLBACK") == "FALLBACK")

    text3 = "## subsection only\n\n# real title here"
    # Only h1 is matched, but we scan top 20 lines - so "real title here" wins
    check("title: scans first 20 lines for h1",
          _extract_title(text3, "fb") == "real title here")


def t_doc_id_prefix():
    a = _doc_id_prefix("/path/a.md")
    b = _doc_id_prefix("/path/b.md")
    c = _doc_id_prefix("/path/a.md")
    check("docid: stable for same path", a == c)
    check("docid: different for different paths", a != b)
    check("docid: 16-char hex prefix", len(a) == 16 and all(ch in "0123456789abcdef" for ch in a))


def main() -> int:
    for fn in (
        t_convert_markdown_passthrough,
        t_convert_txt_passthrough,
        t_chunk_text,
        t_chunk_short_text,
        t_extract_title,
        t_doc_id_prefix,
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
