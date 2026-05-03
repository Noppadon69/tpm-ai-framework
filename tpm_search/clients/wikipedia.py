"""
Wikipedia REST client - definitions / standard reference, no API key, infinite
ref: MASTER_PLAN_v5.md § 6.4.4

Two-stage search:
    1. Direct page lookup via wikipediaapi (full summary, ~1500 chars)
       Best for exact-name queries: "ASTM A106", "ISO 9001", "FMEA"
    2. MediaWiki opensearch fallback (titles + short descriptions)
       For fuzzy / unknown queries.

Why both? Opensearch alone returned wrong sister-articles for engineering
standards (e.g. searching "ASTM A106 standard" got ASTM A500, A36, Astra A-100
- none of which is the actual page). Direct lookup wins for exact names.
"""
from __future__ import annotations

import logging
import time

import httpx

from tpm_search.types import SearchProvider, SearchResult, SearchResults

log = logging.getLogger(__name__)

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

    @staticmethod
    def _candidates(query: str) -> list[str]:
        """Generate page-title variations to try in order of likelihood."""
        q = query.strip()
        out: list[str] = []
        seen: set[str] = set()

        def push(s: str) -> None:
            s = s.strip()
            if s and s.lower() not in seen:
                out.append(s)
                seen.add(s.lower())

        push(q)

        # Strip trailing modifiers
        cleaned = q
        for tail in (" standard", " specification", " spec",
                     " มาตรฐาน", " ตอบเป็นภาษาไทย", " in thai"):
            if cleaned.lower().endswith(tail):
                cleaned = cleaned[: -len(tail)].rstrip()
                break
        push(cleaned)

        # Strip leading "ASTM" / "ISO" prefix - sometimes the page is just "A106"
        for prefix in ("ASTM ", "ISO ", "JIS ", "DIN ", "EN "):
            if cleaned.upper().startswith(prefix):
                push(cleaned[len(prefix):])

        # Combined-spec form: "A106/A106M" -> "A106"
        if "/" in cleaned:
            push(cleaned.split("/", 1)[0].strip())

        return out[:6]  # cap

    @staticmethod
    def _is_disambiguation(title: str, summary: str) -> bool:
        """
        Heuristic: skip disambiguation pages - they're not useful answers.
        Indicators:
          - title appears in Category:Disambiguation_pages (we can't easily check)
          - summary starts with 'X may refer to:'
          - summary contains 'อาจหมายถึง' (Thai)
          - summary is very short with bullet-like patterns
        """
        s = (summary or "").strip()
        first_line = s.split("\n", 1)[0].lower()
        if "may refer to" in first_line or "อาจหมายถึง" in first_line:
            return True
        # Very short summary (< 200 chars) + multiple newlines = listy disambig
        if len(s) < 200 and s.count("\n") >= 2:
            return True
        return False

    def _try_direct(self, candidate: str, results: list[SearchResult]) -> bool:
        """Append a direct page hit if the page exists AND is a real article."""
        if not candidate.strip():
            return False
        try:
            wiki = self._get_wiki()
            page = wiki.page(candidate)
            if not page.exists():
                return False
            summary = (page.summary or "")[:1500]
            if self._is_disambiguation(page.title, summary):
                log.debug("skip disambiguation page: %r", page.title)
                return False
            if any(r.url == page.fullurl for r in results):
                return True
            results.append(SearchResult(
                title=page.title,
                url=page.fullurl,
                snippet=summary,
                source_engine="wikipedia_direct",
            ))
            return True
        except Exception as e:  # noqa: BLE001
            log.debug("direct lookup of %r failed: %s", candidate, e)
        return False

    def search(self, query: str, max_results: int = 5) -> SearchResults:
        """
        Direct page lookup ONLY (with variations).
        If no direct hit, return empty results so the L3 router falls through
        to SearXNG. We deliberately skip opensearch because it returns wrong
        sister-articles for engineering codes (e.g. ASTM A500 when looking
        for A106) - which is worse than no result.
        """
        t0 = time.perf_counter()
        results: list[SearchResult] = []

        for cand in self._candidates(query):
            if self._try_direct(cand, results):
                break  # one good hit is enough

        return SearchResults(
            provider=SearchProvider.WIKIPEDIA,
            query=query,
            results=results[:max_results],
            latency_ms=int((time.perf_counter() - t0) * 1000),
        )

    def get_page_summary(self, title: str) -> str:
        """Get full page summary for a known title."""
        wiki = self._get_wiki()
        page = wiki.page(title)
        if not page.exists():
            return ""
        return page.summary
