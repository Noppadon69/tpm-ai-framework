"""
DuckDuckGo Instant Answer client — no API key, ∞
ref: MASTER_PLAN_v5.md § 6.4.4
"""
from __future__ import annotations

import time

from tpm_search.types import SearchProvider, SearchResult, SearchResults


class DuckDuckGoClient:
    def search(self, query: str, max_results: int = 10, region: str = "wt-wt") -> SearchResults:
        t0 = time.perf_counter()
        try:
            # Try ddgs (newer name) first, fall back to duckduckgo_search
            try:
                from ddgs import DDGS  # type: ignore
            except ImportError:
                from duckduckgo_search import DDGS  # type: ignore

            with DDGS() as ddgs:
                raw_results = list(ddgs.text(query, max_results=max_results, region=region))
        except Exception as e:  # noqa: BLE001
            return SearchResults(
                provider=SearchProvider.DUCKDUCKGO,
                query=query,
                error=f"{type(e).__name__}: {e}",
                latency_ms=int((time.perf_counter() - t0) * 1000),
            )

        results = []
        for item in raw_results:
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("href", "") or item.get("url", ""),
                    snippet=item.get("body", "") or item.get("snippet", ""),
                    raw=item,
                )
            )
        return SearchResults(
            provider=SearchProvider.DUCKDUCKGO,
            query=query,
            results=results,
            latency_ms=int((time.perf_counter() - t0) * 1000),
        )
