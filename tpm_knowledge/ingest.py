"""
tpm_knowledge.ingest - convert + chunk + embed documents into ChromaDB
ref: MASTER_PLAN_v6.md Phase 1 Day 1-3 (G-01: markitdown + llama-index)

Pipeline:
    file.{pdf,docx,xlsx,md,txt,html,...}
       │
       ▼  markitdown (Microsoft, MIT) - lossless conversion
    Markdown text
       │
       ▼  llama-index SentenceSplitter - 512 tok chunks, 50 tok overlap
    list[chunk_text]
       │
       ▼  OllamaEmbedding (bge-m3) - 1024-dim embeddings
    list[(chunk_text, embedding, metadata)]
       │
       ▼  ChromaDB (persistent at chroma_db/)
    collection 'tpm_wiki' grows by N

ChromaDB collection design:
  - name: 'tpm_wiki' (public/internal docs)
  - id format: '<sha256(path)[:16]>_<chunk_idx>'
  - metadata: source_path, filename, chunk_idx, ingested_at,
              classification (PUBLIC|INTERNAL|CONFIDENTIAL), title

Idempotent: re-ingesting the same path replaces old chunks for that path.
"""
from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
CHROMA_DIR = REPO_ROOT / "chroma_db"
COLLECTION_NAME = "tpm_wiki"

# Embedding model - bge-m3 multilingual (Thai + EN) at 1024-dim
EMBED_MODEL = "bge-m3"


# ============================================================
# Lazy clients (heavy imports are avoided on module load)
# ============================================================
_chroma_client = None
_collection = None
_embed_model = None
_splitter = None


def _get_chroma():
    """Lazy chromadb persistent client."""
    global _chroma_client, _collection
    if _collection is None:
        import chromadb
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _collection = _chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "TPM AI public/internal knowledge wiki"},
        )
    return _collection


def _get_embed():
    """Lazy OllamaEmbedding client."""
    global _embed_model
    if _embed_model is None:
        from llama_index.embeddings.ollama import OllamaEmbedding
        _embed_model = OllamaEmbedding(model_name=EMBED_MODEL)
    return _embed_model


def _get_splitter():
    """Lazy SentenceSplitter."""
    global _splitter
    if _splitter is None:
        from llama_index.core.node_parser import SentenceSplitter
        _splitter = SentenceSplitter(chunk_size=512, chunk_overlap=50)
    return _splitter


# ============================================================
# Conversion
# ============================================================
def convert_to_markdown(file_path: Path) -> str:
    """
    Use markitdown to convert any supported file into Markdown text.
    Plain text/markdown files short-circuit (no point invoking the converter).
    """
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(p)

    if p.suffix.lower() in {".md", ".markdown", ".txt"}:
        return p.read_text(encoding="utf-8", errors="replace")

    from markitdown import MarkItDown
    md = MarkItDown()
    result = md.convert(str(p))
    return result.text_content or ""


# ============================================================
# Chunking
# ============================================================
def chunk_text(text: str) -> list[str]:
    """Split markdown into semantic chunks via llama-index SentenceSplitter."""
    splitter = _get_splitter()
    return splitter.split_text(text)


# ============================================================
# Ingest
# ============================================================
@dataclass
class IngestResult:
    source_path: str
    n_chunks: int
    chunk_chars_total: int
    classification: str
    skipped_reason: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.skipped_reason is None


def _extract_title(md_text: str, fallback: str) -> str:
    for line in md_text.splitlines()[:20]:
        m = re.match(r"^#\s+(.+?)\s*$", line)
        if m:
            return m.group(1).strip()
    return fallback


def _doc_id_prefix(source_path: str) -> str:
    return hashlib.sha256(source_path.encode("utf-8")).hexdigest()[:16]


def ingest_file(
    file_path: Path | str,
    *,
    classification: str = "INTERNAL",
) -> IngestResult:
    """
    Convert + chunk + embed + upsert one file into the ChromaDB collection.
    Replaces any prior chunks for the same source_path.

    classification: PUBLIC | INTERNAL | CONFIDENTIAL | RESTRICTED
       - Used by L3 search egress check (CONFIDENTIAL+ blocks web search)
       - Default INTERNAL (= safest assumption for unspecified docs)
    """
    p = Path(file_path).resolve()
    md_text = convert_to_markdown(p)
    if not md_text.strip():
        return IngestResult(
            source_path=str(p), n_chunks=0, chunk_chars_total=0,
            classification=classification, skipped_reason="empty after conversion",
        )

    chunks = chunk_text(md_text)
    if not chunks:
        return IngestResult(
            source_path=str(p), n_chunks=0, chunk_chars_total=0,
            classification=classification, skipped_reason="no chunks produced",
        )

    title = _extract_title(md_text, p.stem)
    prefix = _doc_id_prefix(str(p))
    ingested_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # Remove prior chunks for the same source (idempotent re-ingest)
    collection = _get_chroma()
    try:
        existing = collection.get(where={"source_path": str(p)})
        if existing and existing.get("ids"):
            collection.delete(ids=existing["ids"])
            log.info("removed %d prior chunks for %s", len(existing["ids"]), p.name)
    except Exception as e:  # noqa: BLE001
        log.warning("could not check for prior chunks: %s", e)

    # Embed all chunks (single batch - keeps Ollama warm)
    embed = _get_embed()
    embeddings = embed.get_text_embedding_batch(chunks, show_progress=False)

    ids = [f"{prefix}_{i:04d}" for i in range(len(chunks))]
    metadatas = [
        {
            "source_path": str(p),
            "filename": p.name,
            "chunk_idx": i,
            "title": title,
            "classification": classification,
            "ingested_at": ingested_at,
        }
        for i in range(len(chunks))
    ]

    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    return IngestResult(
        source_path=str(p),
        n_chunks=len(chunks),
        chunk_chars_total=sum(len(c) for c in chunks),
        classification=classification,
    )


def list_documents() -> list[dict]:
    """Return a deduped list of {source_path, filename, classification, n_chunks}."""
    collection = _get_chroma()
    try:
        all_meta = collection.get()
    except Exception as e:  # noqa: BLE001
        log.error("failed to list documents: %s", e)
        return []
    metadatas = all_meta.get("metadatas") or []
    buckets: dict[str, dict] = {}
    for m in metadatas:
        sp = m.get("source_path", "?")
        if sp not in buckets:
            buckets[sp] = {
                "source_path": sp,
                "filename": m.get("filename", ""),
                "classification": m.get("classification", "?"),
                "title": m.get("title", ""),
                "n_chunks": 0,
                "ingested_at": m.get("ingested_at", ""),
            }
        buckets[sp]["n_chunks"] += 1
    return sorted(buckets.values(), key=lambda d: d["filename"])
