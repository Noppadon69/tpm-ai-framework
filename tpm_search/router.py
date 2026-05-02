"""
tpm_search.router — Lane-based L3 routing
ref: MASTER_PLAN_v5.md § 6.4.0

Lanes (per § 6.4.0):
  Wikipedia   → definition / standard reference
  Exa         → structured + grounding (citations)
  Tavily      → AI-clean for LLM (recent / current)
  SearXNG     → workhorse 80% (∞ free)
  DuckDuckGo  → simple lookup fallback (no key, ∞)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from tpm_search.clients import (
    DuckDuckGoClient,
    ExaClient,
    JinaReaderClient,
    SearXNGClient,
    TavilyClient,
    WikipediaClient,
)
from tpm_search.egress import EgressBlocked, check_egress, classify
from tpm_search.types import (
    Classification,
    Intent,
    SearchProvider,
    SearchResults,
)

log = logging.getLogger(__name__)


@dataclass
class LaneDecision:
    primary: SearchProvider
    fallbacks: list[SearchProvider]
    reason: str


# ============================================================
# Lane assignment
# ============================================================
def pick_lane(intent: Intent) -> LaneDecision:
    if intent.is_definition or intent.is_standard_reference:
        return LaneDecision(
            primary=SearchProvider.WIKIPEDIA,
            fallbacks=[SearchProvider.SEARXNG, SearchProvider.DUCKDUCKGO],
            reason="definition/standard → Wikipedia first",
        )

    if intent.needs_grounding or intent.has_output_schema:
        return LaneDecision(
            primary=SearchProvider.EXA,
            fallbacks=[SearchProvider.TAVILY, SearchProvider.SEARXNG],
            reason="structured/cited → Exa primary",
        )

    if intent.feed_to_llm and intent.is_recent:
        return LaneDecision(
            primary=SearchProvider.TAVILY,
            fallbacks=[SearchProvider.SEARXNG, SearchProvider.DUCKDUCKGO],
            reason="recent + LLM-context → Tavily",
        )

    if intent.is_simple_lookup:
        return LaneDecision(
            primary=SearchProvider.SEARXNG,
            fallbacks=[SearchProvider.DUCKDUCKGO],
            reason="simple lookup → workhorse",
        )

    # Default: workhorse
    return LaneDecision(
        primary=SearchProvider.SEARXNG,
        fallbacks=[SearchProvider.DUCKDUCKGO, SearchProvider.TAVILY],
        reason="default workhorse",
    )


# ============================================================
# L3 Router (sync — async wrapper provided in Phase 2)
# ============================================================
class L3Router:
    def __init__(self):
        self._clients: dict[SearchProvider, object] = {
            SearchProvider.SEARXNG: SearXNGClient(),
            SearchProvider.TAVILY: TavilyClient(),
            SearchProvider.EXA: ExaClient(),
            SearchProvider.DUCKDUCKGO: DuckDuckGoClient(),
            SearchProvider.WIKIPEDIA: WikipediaClient(),
            SearchProvider.JINA: JinaReaderClient(),
        }

    def search(
        self,
        query: str,
        intent: Intent | None = None,
        classification: Classification | None = None,
        max_results: int = 10,
        min_useful: int = 1,
    ) -> SearchResults:
        intent = intent or Intent()

        # 1. Egress check (raises EgressBlocked → caller catches)
        cls = classification or classify(query)
        if intent.forbid_external or cls in (
            Classification.CONFIDENTIAL,
            Classification.RESTRICTED,
        ):
            raise EgressBlocked(
                f"L3 search blocked: classification={cls.value}, "
                f"forbid_external={intent.forbid_external}"
            )
        check_egress(query, "L3_search", classification=cls)

        # 2. Lane selection
        decision = pick_lane(intent)
        chain = [decision.primary] + decision.fallbacks
        log.info(
            "L3 route: query=%r lane=%s reason=%s",
            query, decision.primary.value, decision.reason,
        )

        # 3. Try chain
        tried: list[SearchProvider] = []
        last_result: SearchResults | None = None
        for provider in chain:
            tried.append(provider)
            result = self._call(provider, query, intent, max_results)
            result.fallback_chain = tried.copy()
            result.classification = cls
            if result.is_useful(min_useful):
                return result
            last_result = result
            log.warning(
                "%s: not useful (results=%d, error=%r), trying next",
                provider.value,
                len(result.results),
                result.error,
            )

        # 4. None worked
        if last_result is None:
            return SearchResults(
                provider=chain[-1],
                query=query,
                error="no providers attempted",
                fallback_chain=tried,
                classification=cls,
            )
        last_result.error = (last_result.error or "") + " | exhausted all lanes"
        return last_result

    # ---------- per-provider dispatch ----------
    def _call(
        self,
        provider: SearchProvider,
        query: str,
        intent: Intent,
        max_results: int,
    ) -> SearchResults:
        client = self._clients[provider]
        if provider == SearchProvider.SEARXNG:
            return client.search(query, max_results=max_results)
        if provider == SearchProvider.TAVILY:
            return client.search(query, max_results=max_results)
        if provider == SearchProvider.EXA:
            return client.search(
                query,
                num_results=max_results,
                search_type="deep" if intent.is_research else "auto",
                output_schema=intent.output_schema,
            )
        if provider == SearchProvider.DUCKDUCKGO:
            return client.search(query, max_results=max_results)
        if provider == SearchProvider.WIKIPEDIA:
            return client.search(query, max_results=max_results)
        if provider == SearchProvider.JINA:
            return client.fetch(query)
        raise ValueError(f"unknown provider: {provider}")


# ============================================================
# Module-level convenience
# ============================================================
_default_router: L3Router | None = None


def search(
    query: str,
    intent: Intent | None = None,
    classification: Classification | None = None,
    max_results: int = 10,
) -> SearchResults:
    """Convenience: use the default singleton router."""
    global _default_router
    if _default_router is None:
        _default_router = L3Router()
    return _default_router.search(
        query, intent=intent, classification=classification, max_results=max_results
    )
