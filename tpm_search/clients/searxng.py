"""
SearXNG client — workhorse provider (∞ free, self-hosted)
ref: MASTER_PLAN_v5.md § 6.4.1
"""
from __future__ import annotations

import os
import time

import httpx

from tpm_search.types import SearchProvider, SearchResult, SearchResults


class SearXNGClient:
    def __init__(self, base_url: str | None = None, timeout: float = 10.0):
        self.base_url = (
            base_url
            or os.getenv("SEARXNG_URL", "http://localhost:8888")
        ).rstrip("/")
        self.timeout = timeout

    def search(
        self,
        query: str,
        max_results: int = 10,
        language: str = "en",
        categories: str = "general",
    ) -> SearchResults:
        t0 = time.perf_counter()
        try:
            r = httpx.get(
                f"{self.base_url}/search",
                params={
                    "q": query,
                    "format": "json",
                    "language": language,
                    "categories": categories,
                },
                timeout=self.timeout,
            )
            r.raise_for_status()
            data = r.json()
        except Exception as e:  # noqa: BLE001
            return SearchResults(
                provider=SearchProvider.SEARXNG,
                query=query,
                error=f"{type(e).__name__}: {e}",
                latency_ms=int((time.perf_counter() - t0) * 1000),
            )

        results = []
        for item in (data.get("results") or [])[:max_results]:
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", ""),
                    score=item.get("score"),
                    published=item.get("publishedDate"),
                    source_engine=item.get("engine"),
                    raw=item,
                )
            )
        return SearchResults(
            provider=SearchProvider.SEARXNG,
            query=query,
            results=results,
            latency_ms=int((time.perf_counter() - t0) * 1000),
        )

    def health(self) -> bool:
        """Quick liveness check — used by router to decide fallback."""
        try:
            r = httpx.get(f"{self.base_url}/healthz", timeout=2.0)
            return r.status_code == 200
        except Exception:
            return False
