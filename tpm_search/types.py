"""
tpm_search.types — common data models
ref: MASTER_PLAN_v5.md § 6.4, § 21.1
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ============================================================
# Classification — egress policy enforcement (§ 21.1)
# ============================================================
class Classification(str, Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


# ============================================================
# Intent — drives lane selection in router (§ 6.4.0)
# ============================================================
class Intent(BaseModel):
    """
    Lane signals for the L3 router. Filled by orchestrator before
    calling search(). Defaults are conservative (workhorse SearXNG).
    """
    is_definition: bool = False           # → Wikipedia lane
    is_standard_reference: bool = False   # → Wikipedia lane
    needs_grounding: bool = False         # → Exa lane (with citations)
    has_output_schema: bool = False       # → Exa lane (structured)
    output_schema: Optional[dict[str, Any]] = None
    feed_to_llm: bool = False             # → Tavily lane (AI-cleaned)
    is_recent: bool = False               # → Tavily lane
    is_research: bool = False             # → Exa deep mode
    is_simple_lookup: bool = False        # → DDG lane
    forbid_external: bool = False         # block all L3 (e.g., L1 forced)


# ============================================================
# Provider enum — for logging + quota tracking
# ============================================================
class SearchProvider(str, Enum):
    SEARXNG = "searxng"
    TAVILY = "tavily"
    EXA = "exa"
    DUCKDUCKGO = "duckduckgo"
    WIKIPEDIA = "wikipedia"
    JINA = "jina"


# ============================================================
# Result models
# ============================================================
class SearchResult(BaseModel):
    """One search hit, normalized across providers."""
    title: str = ""
    url: str = ""
    snippet: str = ""
    score: Optional[float] = None         # relevance, if provider supplies
    published: Optional[str] = None       # ISO date string
    source_engine: Optional[str] = None   # which underlying engine (e.g., google, bing)
    raw: dict[str, Any] = Field(default_factory=dict)  # provider-specific extras


class Grounding(BaseModel):
    """Per-field citations (Exa-style). Empty for non-Exa providers."""
    field: str
    citations: list[dict[str, Any]] = Field(default_factory=list)
    confidence: Optional[str] = None       # "low" | "medium" | "high"


class SearchResults(BaseModel):
    """Bundle of results from one provider call."""
    provider: SearchProvider
    query: str
    results: list[SearchResult] = Field(default_factory=list)
    structured_output: Optional[dict[str, Any]] = None  # Exa output.content
    grounding: list[Grounding] = Field(default_factory=list)
    fetched_at: datetime = Field(default_factory=_utcnow)
    latency_ms: Optional[int] = None
    quota_remaining: Optional[int] = None
    error: Optional[str] = None
    fallback_chain: list[SearchProvider] = Field(default_factory=list)
    classification: Classification = Classification.PUBLIC

    def is_useful(self, min_results: int = 1) -> bool:
        if self.error:
            return False
        if self.structured_output:
            return True
        return len(self.results) >= min_results
