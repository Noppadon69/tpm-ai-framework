"""
tpm_knowledge - Layer 1 ingest + retrieval (markitdown + llama-index + ChromaDB)
ref: MASTER_PLAN_v6.md Phase 1 Day 1-3 (G-01 patch: markitdown replaces openkb)
"""
from tpm_knowledge.ingest import (
    IngestResult,
    chunk_text,
    convert_to_markdown,
    ingest_file,
    list_documents,
)
from tpm_knowledge.query import QueryHit, search_chunks

__all__ = [
    "IngestResult",
    "QueryHit",
    "chunk_text",
    "convert_to_markdown",
    "ingest_file",
    "list_documents",
    "search_chunks",
]
