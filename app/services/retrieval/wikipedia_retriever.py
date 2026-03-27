"""
Wikipedia Retrieval - Layer 3A
Retrieves factual/encyclopedic information from Wikipedia API.
"""

from typing import Optional
import wikipediaapi
from app.core.logging import get_logger

logger = get_logger(__name__)


class WikipediaRetriever:
    """
    Retrieves evidence from Wikipedia for encyclopedic claims.

    Best for: named entities, historical facts, scientific concepts,
    biographical info, places, organizations.
    """

    def __init__(self):
        """Initialize Wikipedia retriever with API client."""
        self.wiki = wikipediaapi.Wikipedia(
            user_agent="AIHallucinationDetector/0.1 (academic project)",
            language="en",
        )

    def search(self, query: str, max_results: int = 2) -> dict:
        """
        Search Wikipedia for a claim.

        1. Look up Wikipedia page by query
        2. Check if page exists
        3. Extract summary (first ~2 paragraphs)
        4. Return structured evidence

        Args:
            query: Search query/extracted claim
            max_results: Number of paragraph sections to extract

        Returns:
            Dictionary with title, content, url, relevance_score, found
        """
        logger.info(f"Searching Wikipedia for: {query}")

        try:
            page = self.wiki.page(query)

            if not page.exists():
                logger.info(f"Wikipedia page not found for: {query}")
                return {
                    "title": None,
                    "content": None,
                    "url": None,
                    "relevance_score": 0.0,
                    "found": False,
                }

            # Extract summary (Wikipedia API gives first section)
            summary = page.summary
            if not summary:
                logger.info(f"Wikipedia page found but no summary: {query}")
                return {
                    "title": page.title,
                    "content": None,
                    "url": page.fullurl,
                    "relevance_score": 0.0,
                    "found": False,
                }

            # Trim to first ~2 paragraphs (split on double newline)
            paragraphs = summary.split("\n")
            content = "\n".join(paragraphs[:max_results])

            # Simple relevance: check if query words appear in content
            query_words = set(query.lower().split())
            content_lower = content.lower()
            matching = sum(1 for w in query_words if w in content_lower)
            relevance = matching / max(len(query_words), 1)

            logger.info(
                f"Wikipedia found: '{page.title}' | "
                f"{len(content)} chars, relevance={relevance:.2f}"
            )

            return {
                "title": page.title,
                "content": content,
                "url": page.fullurl,
                "relevance_score": round(relevance, 2),
                "found": True,
            }

        except Exception as e:
            logger.error(f"Wikipedia search failed: {e}", exc_info=True)
            return {
                "title": None,
                "content": None,
                "url": None,
                "relevance_score": 0.0,
                "found": False,
            }

    def get_evidence(self, claim: str) -> Optional[str]:
        """
        Get evidence text for a specific claim.

        Args:
            claim: The factual claim to verify

        Returns:
            Evidence text if found, None otherwise
        """
        result = self.search(claim)
        if result.get("found"):
            return result.get("content")
        return None
