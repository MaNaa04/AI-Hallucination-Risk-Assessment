"""
SerpAPI Retrieval - Layer 3
Retrieves live web results for recent events and current information.
"""

from typing import Optional
from serpapi import GoogleSearch
from app.core.logging import get_logger
from app.core.config import get_settings

logger = get_logger(__name__)


class SerpAPIRetriever:
    """
    Retrieves evidence from Google Search via SerpAPI.

    Best for: recent events (< 1 year), statistics, current affairs,
    news, trending topics.

    Note: SerpAPI costs money per call, so we gate it:
    - Only call if Wikipedia returns nothing useful
    - Only for 'recent_event' query type
    """

    def __init__(self):
        """Initialize SerpAPI retriever."""
        settings = get_settings()
        self.api_key = settings.serpapi_key

    def search(self, query: str, max_results: int = 3) -> dict:
        """
        Search Google via SerpAPI for a claim.

        Args:
            query: Search query/extracted claim
            max_results: Number of results to retrieve (typically 3)

        Returns:
            Dictionary with keys:
            - 'results': List of results with 'title', 'snippet', 'url'
            - 'search_metadata': timestamp, etc
            - 'found': True if results found
        """
        if not self.api_key:
            logger.warning("SerpAPI key not configured, skipping search")
            return {"found": False, "results": [], "search_metadata": None}

        logger.info(f"Searching SerpAPI for: {query}")

        try:
            params = {
                "q": query,
                "api_key": self.api_key,
                "engine": "google",
                "num": max_results,
                "gl": "us",
                "hl": "en"
            }

            search = GoogleSearch(params)
            results = search.get_dict()

            # Extract organic results
            organic_results = results.get("organic_results", [])

            if not organic_results:
                logger.info(f"No SerpAPI results found for: {query}")
                return {
                    "found": False,
                    "results": [],
                    "search_metadata": results.get("search_metadata")
                }

            # Format results
            formatted_results = []
            for result in organic_results[:max_results]:
                formatted_results.append({
                    "title": result.get("title", ""),
                    "snippet": result.get("snippet", ""),
                    "url": result.get("link", ""),
                    "source": result.get("source", "")
                })

            logger.info(f"Found {len(formatted_results)} SerpAPI results")
            return {
                "found": True,
                "results": formatted_results,
                "search_metadata": results.get("search_metadata")
            }

        except Exception as e:
            logger.error(f"SerpAPI search error: {e}", exc_info=True)
            return {
                "found": False,
                "results": [],
                "search_metadata": None,
                "error": str(e)
            }

    def get_evidence(self, claim: str) -> Optional[str]:
        """
        Get evidence from web search for a specific claim.

        Args:
            claim: The factual claim to verify

        Returns:
            Combined snippets as evidence text
        """
        result = self.search(claim)
        if result.get('found') and result.get('results'):
            evidence_parts = []
            for r in result['results']:
                title = r.get('title', '')
                snippet = r.get('snippet', '')
                source = r.get('source', 'Web')
                if snippet:
                    evidence_parts.append(f"[{source}] {title}: {snippet}")

            return "[Source: Google Search]\n" + '\n\n'.join(evidence_parts)
        return None
