"""
Wikipedia REST client — definitions / standard reference, no API key, ∞
ref: MASTER_PLAN_v5.md § 6.4.4
"""
from __future__ import annotations

import time

from tpm_search.types import SearchProvider, SearchResult, SearchResults

USER_AGENT = "tpm-ai/0.1 (https://github.com/local; tpm-intern@local)"


class WikipediaClient:
    def __init__(self, language: str = "en"):
        self.language = language
        self._wiki = None

    def _get_wiki(self):
        if self._wiki is None:
            import wikipediaapi  # type: ignore

            self._wiki = wikipediaapi.Wikipedia(
                user_agent=USER_AGENT,
                language=self.language,
            )
        return self._wiki

    def search(self, query: str, max_results: int = 5) -> SearchResults:
        """
        Wikipedia API doesn't have a 'search' in wikipediaapi — use page lookup directly.
        For multi-result search, fall through to the underlying MediaWiki opensearch.
        """
        t0 = time.perf_counter()
        try:
            import httpx

            api = f"https://{self.language}.wikipedia.org/w/api.php"
            r = httpx.get(
                api,
                params={
                    "action": "opensearch",
                    "search": query,
                    "limit": max_results,
                    "namespace": 0,
                    "format": "json",
                },
                headers={"User-Agent": USER_AGENT},
                timeout=10.0,
            )
            r.raise_for_status()
            # opensearch returns: [query, [titles], [descriptions], [urls]]
            data = r.json()
            titles, descriptions, urls = data[1], data[2], data[3]
        except Exception as e:  # noqa: BLE001
            return SearchResults(
                provider=SearchProvider.WIKIPEDIA,
                query=query,
                error=f"{type(e).__name__}: {e}",
                latency_ms=int((time.perf_counter() - t0) * 1000),
            )

        results = []
        for title, desc, url in zip(titles, descriptions, urls):
            results.append(
                SearchResult(
                    title=title,
                    url=url,
                    snippet=desc,
                    source_engine="wikipedia",
                )
            )
        return SearchResults(
            provider=SearchProvider.WIKIPEDIA,
            query=query,
            results=results,
            latency_ms=int((time.perf_counter() - t0) * 1000),
        )

    def get_page_summary(self, title: str) -> str:
        """Get full page summary for a known title."""
        wiki = self._get_wiki()
        page = wiki.page(title)
        if not page.exists():
            return ""
        return page.summary
