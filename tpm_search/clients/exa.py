"""
Exa client — structured + grounding (1k/mo free)
ref: MASTER_PLAN_v5.md § 6.4.3
       https://docs.exa.ai/reference/search-api-guide-for-coding-agents
"""
from __future__ import annotations

import os
import time
from typing import Any

from tpm_search.quota import increment, is_available, remaining
from tpm_search.types import (
    Grounding,
    SearchProvider,
    SearchResult,
    SearchResults,
)


class ExaClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("EXA_API_KEY")
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not self.api_key:
                raise RuntimeError(
                    "EXA_API_KEY not set (or use MCP OAuth flow per § 6.4.3)"
                )
            from exa_py import Exa
            self._client = Exa(api_key=self.api_key)
        return self._client

    def search(
        self,
        query: str,
        num_results: int = 10,
        search_type: str = "auto",  # auto|fast|instant|deep-lite|deep|deep-reasoning
        output_schema: dict[str, Any] | None = None,
        contents: dict[str, Any] | None = None,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        max_age_hours: int | None = None,
    ) -> SearchResults:
        t0 = time.perf_counter()

        if not is_available(SearchProvider.EXA):
            return SearchResults(
                provider=SearchProvider.EXA,
                query=query,
                error="quota exhausted for the month",
                quota_remaining=0,
            )

        if contents is None:
            contents = {"highlights": True}

        kwargs: dict[str, Any] = {
            "query": query,
            "num_results": num_results,
            "type": search_type,
            "contents": contents,
        }
        if output_schema is not None:
            kwargs["output_schema"] = output_schema
        if include_domains:
            kwargs["include_domains"] = include_domains
        if exclude_domains:
            kwargs["exclude_domains"] = exclude_domains
        if max_age_hours is not None:
            kwargs["max_age_hours"] = max_age_hours

        try:
            client = self._get_client()
            response = client.search(**kwargs)
        except Exception as e:  # noqa: BLE001
            return SearchResults(
                provider=SearchProvider.EXA,
                query=query,
                error=f"{type(e).__name__}: {e}",
                latency_ms=int((time.perf_counter() - t0) * 1000),
            )

        increment(SearchProvider.EXA)

        # Normalize results
        results = []
        for item in getattr(response, "results", []) or []:
            highlights = getattr(item, "highlights", None) or []
            snippet = " | ".join(highlights) if highlights else (
                getattr(item, "text", "") or ""
            )[:500]
            results.append(
                SearchResult(
                    title=getattr(item, "title", "") or "",
                    url=getattr(item, "url", "") or "",
                    snippet=snippet,
                    score=getattr(item, "score", None),
                    published=getattr(item, "published_date", None),
                    raw={
                        "id": getattr(item, "id", None),
                        "highlights": highlights,
                    },
                )
            )

        # Structured output (when output_schema provided)
        structured = None
        grounding_list: list[Grounding] = []
        output = getattr(response, "output", None)
        if output is not None:
            structured = getattr(output, "content", None)
            for g in getattr(output, "grounding", []) or []:
                grounding_list.append(
                    Grounding(
                        field=getattr(g, "field", "") or "",
                        citations=getattr(g, "citations", []) or [],
                        confidence=getattr(g, "confidence", None),
                    )
                )

        return SearchResults(
            provider=SearchProvider.EXA,
            query=query,
            results=results,
            structured_output=structured,
            grounding=grounding_list,
            latency_ms=int((time.perf_counter() - t0) * 1000),
            quota_remaining=remaining(SearchProvider.EXA),
        )

    def get_contents(self, urls: list[str], highlights: bool = True) -> SearchResults:
        """Fetch content for known URLs (cheaper than search)."""
        t0 = time.perf_counter()
        try:
            client = self._get_client()
            response = client.get_contents(urls, highlights=highlights)
        except Exception as e:  # noqa: BLE001
            return SearchResults(
                provider=SearchProvider.EXA,
                query=";".join(urls),
                error=f"{type(e).__name__}: {e}",
                latency_ms=int((time.perf_counter() - t0) * 1000),
            )

        increment(SearchProvider.EXA)
        results = []
        for item in getattr(response, "results", []) or []:
            results.append(
                SearchResult(
                    title=getattr(item, "title", "") or "",
                    url=getattr(item, "url", "") or "",
                    snippet=" | ".join(getattr(item, "highlights", []) or []),
                    raw={"highlights": getattr(item, "highlights", [])},
                )
            )
        return SearchResults(
            provider=SearchProvider.EXA,
            query=";".join(urls),
            results=results,
            latency_ms=int((time.perf_counter() - t0) * 1000),
            quota_remaining=remaining(SearchProvider.EXA),
        )
