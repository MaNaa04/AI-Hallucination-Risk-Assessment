"""
SerpAPI Retrieval - Layer 3B
Retrieves live web results for recent events and current information.
"""

from typing import Optional
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

        Extracts organic search snippets and knowledge graph info.

        Args:
            query: Search query/extracted claim
            max_results: Number of results to retrieve (typically 3)

        Returns:
            Dictionary with results list, search_metadata, and found flag
        """
        if not self.api_key or self.api_key == "your_serpapi_key_here":
            logger.warning("SerpAPI key not configured, skipping search")
            return {"found": False, "results": [], "search_metadata": None}

        logger.info(f"Searching SerpAPI for: {query}")

        try:
            from serpapi import GoogleSearch

            params = {
                "q": query,
                "api_key": self.api_key,
                "engine": "google",
                "num": max_results,
            }

            search = GoogleSearch(params)
            raw = search.get_dict()

            results = []

            # Extract knowledge graph answer box if present
            if "answer_box" in raw:
                box = raw["answer_box"]
                answer = box.get("answer") or box.get("snippet") or box.get("result")
                if answer:
                    results.append({
                        "title": box.get("title", "Answer Box"),
                        "snippet": str(answer),
                        "url": box.get("link", ""),
                        "source": "knowledge_graph",
                    })

            # Extract organic search results
            for item in raw.get("organic_results", [])[:max_results]:
                results.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "url": item.get("link", ""),
                    "source": "organic",
                })

            found = len(results) > 0
            logger.info(f"SerpAPI found {len(results)} results for: {query}")

            return {
                "found": found,
                "results": results,
                "search_metadata": raw.get("search_metadata"),
            }

        except Exception as e:
            logger.error(f"SerpAPI search failed: {e}", exc_info=True)
            return {"found": False, "results": [], "search_metadata": None}

    def get_evidence(self, claim: str) -> Optional[str]:
        """
        Get evidence from web search for a specific claim.

        Args:
            claim: The factual claim to verify

        Returns:
            Combined snippets as evidence text
        """
        result = self.search(claim)
        if result.get("found") and result.get("results"):
            snippets = [r.get("snippet", "") for r in result["results"] if r.get("snippet")]
            return "\n".join(snippets) if snippets else None
        return None
