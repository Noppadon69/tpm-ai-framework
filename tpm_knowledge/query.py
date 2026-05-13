"""
tpm_knowledge.query - retrieve chunks from the ChromaDB tpm_wiki collection.
ref: MASTER_PLAN_v6.md Phase 1 Day 1-3
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

log = logging.getLogger(__name__)


@dataclass
class QueryHit:
    """A single retrieval result."""
    chunk_text: str
    score: float                 # cosine similarity, higher = closer
    source_path: str
    filename: str
    title: str
    chunk_idx: int
    classification: str


def search_chunks(
    query: str,
    k: int = 5,
    *,
    classification_filter: Optional[list[str]] = None,
) -> list[QueryHit]:
    """
    Top-k nearest chunks for `query`.

    classification_filter: limit to docs of these classifications
       e.g. ['PUBLIC', 'INTERNAL'] to exclude CONFIDENTIAL from a public answer.
    """
    from tpm_knowledge.ingest import _get_chroma, _get_embed

    collection = _get_chroma()
    embed = _get_embed()
    q_vec = embed.get_query_embedding(query)

    where = None
    if classification_filter:
        where = {"classification": {"$in": list(classification_filter)}}

    res = collection.query(
        query_embeddings=[q_vec],
        n_results=k,
        where=where,
    )

    ids = (res.get("ids") or [[]])[0]
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]

    hits: list[QueryHit] = []
    for i, doc in enumerate(docs):
        meta = metas[i] if i < len(metas) else {}
        dist = dists[i] if i < len(dists) else 1.0
        # Chroma returns cosine *distance* (0 = identical), convert to similarity
        score = max(0.0, 1.0 - float(dist))
        hits.append(QueryHit(
            chunk_text=doc or "",
            score=round(score, 4),
            source_path=meta.get("source_path", ""),
            filename=meta.get("filename", ""),
            title=meta.get("title", ""),
            chunk_idx=int(meta.get("chunk_idx", 0)),
            classification=meta.get("classification", "?"),
        ))
    return hits
