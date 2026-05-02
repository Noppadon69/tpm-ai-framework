"""
tpm_search — Layer 3 search stack (lane-based)
ref: MASTER_PLAN_v5.md § 6.4

Public API:
    from tpm_search import search, Intent, Classification

Lanes (per § 6.4.0):
    SearXNG (workhorse, infinite)
    Tavily  (AI-clean for LLM, 1k/mo free)
    Exa.ai  (structured + grounding, 1k/mo free)
    DuckDuckGo Instant (no key, infinite)
    Wikipedia REST (no key, infinite)
    Jina Reader (no key, free tier - page fetch)
"""
from tpm_search.types import (
    Classification,
    Intent,
    SearchResult,
    SearchResults,
    SearchProvider,
)
from tpm_search.router import L3Router, search

__all__ = [
    "Classification",
    "Intent",
    "SearchResult",
    "SearchResults",
    "SearchProvider",
    "L3Router",
    "search",
]

__version__ = "0.1.0"
