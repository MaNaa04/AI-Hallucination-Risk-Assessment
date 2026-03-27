"""
Wikipedia Retrieval - Layer 3A
Retrieves factual/encyclopedic information from Wikipedia API.
"""

import re
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

    @staticmethod
    def _extract_search_terms(query: str) -> list[str]:
        """
        Extract search terms from a claim/query.

        Wikipedia API needs article titles, not full sentences.
        We try: full query first, then capitalized words (proper nouns),
        then meaningful noun phrases.

        Args:
            query: A claim like "Paris is the capital of France"

        Returns:
            List of search terms to try, e.g. ["Paris is the capital of France", "Paris", "France"]
        """
        terms = [query]  # Try full query first

        # Extract capitalized words (likely proper nouns / entities)
        capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', query)
        for term in capitalized:
            if term not in terms and len(term) > 2:
                terms.append(term)

        # Extract words longer than 4 chars as fallback
        words = re.findall(r'\b\w{5,}\b', query)
        for word in words:
            if word not in terms and word[0].isupper():
                terms.append(word)

        return terms

    def search(self, query: str, max_results: int = 2) -> dict:
        """
        Search Wikipedia for a claim.

        Tries multiple search terms extracted from the query:
        full query first, then proper nouns, then key terms.

        Args:
            query: Search query/extracted claim
            max_results: Number of paragraph sections to extract

        Returns:
            Dictionary with title, content, url, relevance_score, found
        """
        logger.info(f"Searching Wikipedia for: {query}")

        search_terms = self._extract_search_terms(query)
        logger.info(f"Search terms to try: {search_terms}")

        for term in search_terms:
            try:
                page = self.wiki.page(term)

                if not page.exists():
                    logger.info(f"Wikipedia page not found for: {term}")
                    continue

                # Extract summary
                summary = page.summary
                if not summary:
                    logger.info(f"Wikipedia page found but no summary: {term}")
                    continue

                # Trim to first ~2 paragraphs
                paragraphs = summary.split("\n")
                content = "\n".join(paragraphs[:max_results])

                # Simple relevance: check if query words appear in content
                query_words = set(query.lower().split())
                content_lower = content.lower()
                matching = sum(1 for w in query_words if w in content_lower)
                relevance = matching / max(len(query_words), 1)

                logger.info(
                    f"Wikipedia found: '{page.title}' (via term '{term}') | "
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
                logger.error(f"Wikipedia search failed for '{term}': {e}", exc_info=True)
                continue

        # Nothing found across all terms
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
