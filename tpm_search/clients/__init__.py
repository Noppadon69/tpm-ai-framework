"""tpm_search.clients — one module per L3 search provider."""
from tpm_search.clients.searxng import SearXNGClient
from tpm_search.clients.tavily import TavilyClient
from tpm_search.clients.exa import ExaClient
from tpm_search.clients.duckduckgo import DuckDuckGoClient
from tpm_search.clients.wikipedia import WikipediaClient
from tpm_search.clients.jina import JinaReaderClient

__all__ = [
    "SearXNGClient",
    "TavilyClient",
    "ExaClient",
    "DuckDuckGoClient",
    "WikipediaClient",
    "JinaReaderClient",
]
