"""Search client abstraction for company enrichment."""
from typing import List, Dict, Any, Optional
from src.config import SEARCH_PROVIDER, TAVILY_API_KEY, EXA_API_KEY, SERPAPI_KEY


class SearchResult:
    """Structured search result."""

    def __init__(self, title: str, url: str, snippet: str):
        self.title = title
        self.url = url
        self.snippet = snippet

    def __repr__(self):
        return f"SearchResult(title='{self.title[:50]}...', url='{self.url}')"


class SearchClient:
    """Abstract search client for company information retrieval."""

    def __init__(self, provider: str = None):
        self.provider = provider or SEARCH_PROVIDER

    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """
        Search for company information.

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            List of search results
        """
        if self.provider == "tavily":
            return self._tavily_search(query, max_results)
        elif self.provider == "exa":
            return self._exa_search(query, max_results)
        elif self.provider == "serpapi":
            return self._serpapi_search(query, max_results)
        elif self.provider == "mock":
            return self._mock_search(query, max_results)
        else:
            raise ValueError(f"Unknown search provider: {self.provider}")

    def _tavily_search(self, query: str, max_results: int) -> List[SearchResult]:
        """Search using Tavily API."""
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=TAVILY_API_KEY)

            response = client.search(query, max_results=max_results)

            results = []
            for item in response.get('results', []):
                results.append(SearchResult(
                    title=item.get('title', ''),
                    url=item.get('url', ''),
                    snippet=item.get('content', '')
                ))

            return results
        except Exception as e:
            print(f"⚠ Tavily search error: {str(e)}")
            return []

    def _exa_search(self, query: str, max_results: int) -> List[SearchResult]:
        """Search using Exa API."""
        try:
            from exa_py import Exa
            client = Exa(api_key=EXA_API_KEY)

            response = client.search(
                query,
                num_results=max_results,
                use_autoprompt=True
            )

            results = []
            for item in response.results:
                results.append(SearchResult(
                    title=item.title or '',
                    url=item.url or '',
                    snippet=item.text or ''
                ))

            return results
        except Exception as e:
            print(f"⚠ Exa search error: {str(e)}")
            return []

    def _serpapi_search(self, query: str, max_results: int) -> List[SearchResult]:
        """Search using SerpAPI."""
        try:
            import requests

            params = {
                'api_key': SERPAPI_KEY,
                'q': query,
                'num': max_results
            }

            response = requests.get('https://serpapi.com/search', params=params)
            data = response.json()

            results = []
            for item in data.get('organic_results', [])[:max_results]:
                results.append(SearchResult(
                    title=item.get('title', ''),
                    url=item.get('link', ''),
                    snippet=item.get('snippet', '')
                ))

            return results
        except Exception as e:
            print(f"⚠ SerpAPI search error: {str(e)}")
            return []

    def _mock_search(self, query: str, max_results: int) -> List[SearchResult]:
        """Mock search for testing."""
        # Return canned results for Acme Cloud
        if "acme" in query.lower() and "cloud" in query.lower():
            return [
                SearchResult(
                    title="Acme Cloud - Cloud Infrastructure Management Platform",
                    url="https://www.acmecloud.io",
                    snippet="Acme Cloud is a leading provider of cloud infrastructure management solutions. "
                            "Our AI-powered platform helps enterprises optimize cloud costs and performance. "
                            "Headquarters: San Francisco, CA. Founded 2020."
                ),
                SearchResult(
                    title="Acme Cloud Inc. - LinkedIn",
                    url="https://www.linkedin.com/company/acme-cloud",
                    snippet="Acme Cloud Inc. | Cloud Infrastructure Management | 285 employees on LinkedIn. "
                            "Transforming how enterprises manage multi-cloud environments. "
                            "Visit us at acmecloud.io"
                ),
                SearchResult(
                    title="Acme Cloud Raises $50M Series B - TechCrunch",
                    url="https://technews.example.com/acme-cloud-funding-2025",
                    snippet="San Francisco-based Acme Cloud has raised $50 million in Series B funding. "
                            "The company's domain is acmecloud.io. CEO Sarah Chen announced plans for European expansion."
                ),
                SearchResult(
                    title="About Us - Acme Cloud",
                    url="https://www.acmecloud.io/about",
                    snippet="Acme Cloud (formerly known as Acme Cloud Inc., Acme Cloud LLC) is headquartered in "
                            "San Francisco, California. Contact us at hello@acmecloud.io. "
                            "LinkedIn: linkedin.com/company/acme-cloud"
                ),
                SearchResult(
                    title="Acme Cloud - Crunchbase",
                    url="https://www.crunchbase.com/organization/acme-cloud",
                    snippet="Acme Cloud provides cloud management software. Website: acmecloud.io. "
                            "HQ: San Francisco, California, United States. "
                            "LinkedIn: https://www.linkedin.com/company/acme-cloud/"
                )
            ]

        # Generic fallback
        return [
            SearchResult(
                title=f"Search result for {query}",
                url="https://example.com",
                snippet="No specific information available"
            )
        ]


def format_search_results_for_llm(results: List[SearchResult]) -> str:
    """Format search results for LLM consumption."""
    if not results:
        return "No search results found."

    formatted = []
    for i, result in enumerate(results, 1):
        formatted.append(f"""
Result {i}:
Title: {result.title}
URL: {result.url}
Snippet: {result.snippet}
""".strip())

    return "\n\n".join(formatted)
