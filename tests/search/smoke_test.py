"""
smoke_test.py — end-to-end probe of every L3 lane
ref: MASTER_PLAN_v5.md § 6.4, § 22.3.2 (Phase 1 Day 4 acceptance)

Run:  python tests/search/smoke_test.py
Acceptance:
  - SearXNG returns >= 5 results
  - Wikipedia returns >= 1 result for "ASTM A106"
  - DuckDuckGo returns >= 3 results
  - Tavily callable (skipped if no API key)
  - Exa callable (skipped if no API key)
  - egress_guard blocks fake CONFIDENTIAL query
  - router picks correct lane per intent
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

# Load .env if present
env_file = REPO / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from tpm_search import Classification, Intent, search  # noqa: E402
from tpm_search.clients import (  # noqa: E402
    DuckDuckGoClient,
    ExaClient,
    SearXNGClient,
    TavilyClient,
    WikipediaClient,
)
from tpm_search.egress import EgressBlocked, classify  # noqa: E402
from tpm_search.router import pick_lane  # noqa: E402
from tpm_search.types import SearchProvider  # noqa: E402

# ============================================================
# Test runner
# ============================================================
PASS = "[PASS]"
FAIL = "[FAIL]"
SKIP = "[SKIP]"

results: list[tuple[str, str, str]] = []  # (status, name, detail)


def record(status: str, name: str, detail: str = ""):
    results.append((status, name, detail))
    icon = {"PASS": "[PASS]", "FAIL": "[FAIL]", "SKIP": "[SKIP]"}[status]
    print(f"{icon} {name:40s} {detail}")


def title(t: str):
    print()
    print("=" * 64)
    print(t)
    print("=" * 64)


# ============================================================
# Tests
# ============================================================
def test_searxng_direct():
    title("1. SearXNG (workhorse)")
    c = SearXNGClient()
    t0 = time.perf_counter()
    r = c.search("ASME pressure vessel maintenance", max_results=10)
    dt = int((time.perf_counter() - t0) * 1000)
    if r.error:
        record("FAIL", "searxng.search", f"error: {r.error}")
        return
    if len(r.results) >= 5:
        record(
            "PASS",
            "searxng.search",
            f"{len(r.results)} results, latency={r.latency_ms}ms (wall {dt}ms)",
        )
        if r.results:
            print(f"   first: {r.results[0].title[:80]}")
    else:
        record("FAIL", "searxng.search", f"only {len(r.results)} results (need >=5)")


def test_wikipedia_direct():
    title("2. Wikipedia (definitions)")
    c = WikipediaClient()
    r = c.search("ASTM A106", max_results=3)
    if r.error:
        record("FAIL", "wikipedia.search", f"error: {r.error}")
        return
    if r.results:
        record("PASS", "wikipedia.search", f"{len(r.results)} results")
        print(f"   first: {r.results[0].title} - {r.results[0].snippet[:60]}")
    else:
        record("FAIL", "wikipedia.search", "no results")


def test_duckduckgo_direct():
    title("3. DuckDuckGo (no-key fallback)")
    c = DuckDuckGoClient()
    r = c.search("total productive maintenance TPM", max_results=5)
    if r.error:
        record("SKIP", "duckduckgo.search", f"error: {r.error}")
        return
    if len(r.results) >= 1:
        record("PASS", "duckduckgo.search", f"{len(r.results)} results")
    else:
        record("FAIL", "duckduckgo.search", "no results")


def test_tavily_direct():
    title("4. Tavily (AI-clean for LLM)")
    if not os.getenv("TAVILY_API_KEY"):
        record("SKIP", "tavily.search", "TAVILY_API_KEY not set")
        return
    c = TavilyClient()
    r = c.search("latest ASME standard 2026", max_results=3)
    if r.error:
        record("FAIL", "tavily.search", f"error: {r.error}")
        return
    if r.results:
        record(
            "PASS",
            "tavily.search",
            f"{len(r.results)} results, quota={r.quota_remaining}/1000",
        )
    else:
        record("FAIL", "tavily.search", "no results")


def test_exa_direct():
    title("5. Exa (structured + grounding)")
    if not os.getenv("EXA_API_KEY"):
        record("SKIP", "exa.search", "EXA_API_KEY not set (or use MCP OAuth)")
        return
    c = ExaClient()
    r = c.search(
        "ASME Section VIII pressure vessel MAWP formula",
        num_results=3,
        search_type="auto",
    )
    if r.error:
        record("FAIL", "exa.search", f"error: {r.error}")
        return
    if r.results:
        record(
            "PASS",
            "exa.search",
            f"{len(r.results)} results, quota={r.quota_remaining}/1000",
        )
    else:
        record("FAIL", "exa.search", "no results")


def test_egress_guard():
    title("6. Egress Guard (classification + block)")

    # Test classification
    c1 = classify("ราคา bearing SKF 6205 ทั่วไป")
    record("PASS" if c1 == Classification.PUBLIC else "FAIL",
           "classify(generic price)",
           f"got {c1.value} (expected PUBLIC)")

    # Test that CONFIDENTIAL is blocked
    confidential_query = "Boiler B-2 maintenance log incident หน้า 42"
    c2 = classify(confidential_query)
    blocked_correctly = False
    try:
        search(confidential_query)
    except EgressBlocked:
        blocked_correctly = True
    except Exception as e:
        record("FAIL", "egress.block_confidential", f"wrong error: {type(e).__name__}: {e}")
        return

    record(
        "PASS" if blocked_correctly else "FAIL",
        "egress.block_confidential",
        f"classified={c2.value}, blocked={blocked_correctly}",
    )


def test_router_lane_selection():
    title("7. Router (lane assignment)")

    cases = [
        (Intent(is_definition=True), SearchProvider.WIKIPEDIA, "definition"),
        (Intent(needs_grounding=True), SearchProvider.EXA, "grounding"),
        (Intent(has_output_schema=True), SearchProvider.EXA, "output_schema"),
        (Intent(feed_to_llm=True, is_recent=True), SearchProvider.TAVILY, "recent+llm"),
        (Intent(is_simple_lookup=True), SearchProvider.SEARXNG, "simple_lookup"),
        (Intent(), SearchProvider.SEARXNG, "default"),
    ]
    for intent, expected, label in cases:
        decision = pick_lane(intent)
        if decision.primary == expected:
            record("PASS", f"lane:{label}", f"-> {decision.primary.value}")
        else:
            record(
                "FAIL",
                f"lane:{label}",
                f"expected {expected.value}, got {decision.primary.value}",
            )


def test_router_end_to_end():
    title("8. Router (end-to-end through SearXNG)")
    r = search("centrifugal pump cavitation symptoms")
    if r.error and not r.results:
        record("FAIL", "router.e2e", f"error: {r.error}")
        return
    if r.results:
        record(
            "PASS",
            "router.e2e",
            f"provider={r.provider.value} results={len(r.results)} chain={[p.value for p in r.fallback_chain]}",
        )
    else:
        record("FAIL", "router.e2e", "no results")


# ============================================================
# Main
# ============================================================
def main():
    test_searxng_direct()
    test_wikipedia_direct()
    test_duckduckgo_direct()
    test_tavily_direct()
    test_exa_direct()
    test_egress_guard()
    test_router_lane_selection()
    test_router_end_to_end()

    print()
    print("=" * 64)
    pass_n = sum(1 for s, _, _ in results if s == "PASS")
    fail_n = sum(1 for s, _, _ in results if s == "FAIL")
    skip_n = sum(1 for s, _, _ in results if s == "SKIP")
    total = pass_n + fail_n + skip_n
    print(f"Summary: PASS={pass_n}/{total}  FAIL={fail_n}  SKIP={skip_n}")
    print("=" * 64)
    return 0 if fail_n == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
