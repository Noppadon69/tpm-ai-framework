"""
Jina Reader client — page fetch fallback (no API key, free tier)
ref: MASTER_PLAN_v5.md § 6.4.4

Strategy: GET https://r.jina.ai/<URL> returns clean Markdown
"""
from __future__ import annotations

import time

import httpx

from tpm_search.types import SearchProvider, SearchResult, SearchResults


class JinaReaderClient:
    BASE = "https://r.jina.ai"

    def fetch(self, url: str, timeout: float = 30.0) -> SearchResults:
        """Return clean Markdown content for a URL."""
        t0 = time.perf_counter()
        try:
            r = httpx.get(
                f"{self.BASE}/{url}",
                timeout=timeout,
                headers={"Accept": "text/markdown"},
                follow_redirects=True,
            )
            r.raise_for_status()
            content = r.text
        except Exception as e:  # noqa: BLE001
            return SearchResults(
                provider=SearchProvider.JINA,
                query=url,
                error=f"{type(e).__name__}: {e}",
                latency_ms=int((time.perf_counter() - t0) * 1000),
            )

        # Jina prepends "Title: <title>" then content as markdown
        title = ""
        snippet = content
        if content.startswith("Title:"):
            lines = content.split("\n", 2)
            title = lines[0].replace("Title:", "").strip() if lines else ""
            snippet = lines[2] if len(lines) > 2 else content

        return SearchResults(
            provider=SearchProvider.JINA,
            query=url,
            results=[
                SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet[:1000],  # preview only
                    raw={"full_markdown": snippet, "char_count": len(snippet)},
                )
            ],
            latency_ms=int((time.perf_counter() - t0) * 1000),
        )

    # Alias for symmetry with other clients
    def search(self, query: str, max_results: int = 1) -> SearchResults:
        """Treat query as URL — for use when caller has the URL."""
        return self.fetch(query)
