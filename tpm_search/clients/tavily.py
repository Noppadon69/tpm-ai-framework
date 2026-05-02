"""
Tavily client — AI-optimized output for LLM context (1k/mo free)
ref: MASTER_PLAN_v5.md § 6.4.2
"""
from __future__ import annotations

import os
import time

from tpm_search.quota import increment, is_available, remaining
from tpm_search.types import SearchProvider, SearchResult, SearchResults


class TavilyClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not self.api_key:
                raise RuntimeError("TAVILY_API_KEY not set")
            from tavily import TavilyClient as _Tavily
            self._client = _Tavily(api_key=self.api_key)
        return self._client

    def search(
        self,
        query: str,
        max_results: int = 5,
        search_depth: str = "advanced",  # "basic" | "advanced"
        include_raw_content: bool = False,
    ) -> SearchResults:
        t0 = time.perf_counter()

        if not is_available(SearchProvider.TAVILY):
            return SearchResults(
                provider=SearchProvider.TAVILY,
                query=query,
                error="quota exhausted for the month",
                quota_remaining=0,
            )

        try:
            client = self._get_client()
            data = client.search(
                query=query,
                max_results=max_results,
                search_depth=search_depth,
                include_raw_content=include_raw_content,
            )
        except Exception as e:  # noqa: BLE001
            return SearchResults(
                provider=SearchProvider.TAVILY,
                query=query,
                error=f"{type(e).__name__}: {e}",
                latency_ms=int((time.perf_counter() - t0) * 1000),
            )

        increment(SearchProvider.TAVILY)

        results = []
        for item in data.get("results", []):
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", ""),
                    score=item.get("score"),
                    published=item.get("published_date"),
                    raw=item,
                )
            )
        return SearchResults(
            provider=SearchProvider.TAVILY,
            query=query,
            results=results,
            latency_ms=int((time.perf_counter() - t0) * 1000),
            quota_remaining=remaining(SearchProvider.TAVILY),
        )
