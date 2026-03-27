"""
Wikipedia Retrieval - Layer 3
Retrieves factual/encyclopedic information from Wikipedia API.
"""

import wikipediaapi
from typing import Optional
from app.core.logging import get_logger

logger = get_logger(__name__)


class WikipediaRetriever:
    """
    Retrieves evidence from Wikipedia for encyclopedic claims.

    Best for: named entities, historical facts, scientific concepts,
    biographical info, places, organizations.
    """

    def __init__(self, language: str = "en"):
        """Initialize Wikipedia retriever."""
        self.wiki = wikipediaapi.Wikipedia(
            user_agent="AIHallucinationDetector/1.0 (https://github.com/example)",
            language=language
        )

    def search(self, query: str, max_paragraphs: int = 2) -> dict:
        """
        Search Wikipedia for a claim and extract relevant content.

        Args:
            query: Search query/extracted claim
            max_paragraphs: Number of paragraphs to extract

        Returns:
            Dictionary with article info and content
        """
        logger.info(f"Searching Wikipedia for: {query}")

        try:
            # Try to get the page directly
            page = self.wiki.page(query)

            if not page.exists():
                # Try searching with different variations
                variations = self._generate_search_variations(query)
                for variation in variations:
                    page = self.wiki.page(variation)
                    if page.exists():
                        break

            if not page.exists():
                logger.info(f"No Wikipedia page found for: {query}")
                return {
                    "title": None,
                    "content": None,
                    "url": None,
                    "relevance_score": 0.0,
                    "found": False
                }

            # Extract summary (first paragraphs)
            content = self._extract_content(page, max_paragraphs)

            logger.info(f"Found Wikipedia article: {page.title}")
            return {
                "title": page.title,
                "content": content,
                "url": page.fullurl,
                "relevance_score": self._calculate_relevance(query, page.title),
                "found": True
            }

        except Exception as e:
            logger.error(f"Wikipedia search error: {e}", exc_info=True)
            return {
                "title": None,
                "content": None,
                "url": None,
                "relevance_score": 0.0,
                "found": False
            }

    def _generate_search_variations(self, query: str) -> list[str]:
        """Generate search variations for better matching."""
        variations = []

        # Common stop words to filter out
        stop_words = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'of', 'in', 'on', 'at', 'to', 'for', 'with', 'by', 'from',
            'and', 'or', 'but', 'that', 'this', 'it', 'its', 'as', 'has', 'have'
        }

        words = query.split()

        # Extract capitalized words (proper nouns) - these are often Wikipedia articles
        capitalized = [w.strip('.,!?()[]') for w in words
                       if w and w[0].isupper() and w.lower() not in stop_words]
        if capitalized:
            # Try each capitalized word individually
            for word in capitalized:
                if len(word) > 1:
                    variations.append(word)
            # Try combinations
            if len(capitalized) >= 2:
                variations.append(" ".join(capitalized[:2]))

        # Extract non-stop words for keyword search
        keywords = [w.strip('.,!?()[]') for w in words
                    if w.lower() not in stop_words and len(w) > 2]
        if keywords:
            # Try first significant keyword
            variations.append(keywords[0].title())
            # Try first two keywords
            if len(keywords) >= 2:
                variations.append(f"{keywords[0]} {keywords[1]}".title())

        # Title case of original
        variations.append(query.title())

        # Remove duplicates while preserving order
        seen = set()
        unique_variations = []
        for v in variations:
            if v.lower() not in seen and v:
                seen.add(v.lower())
                unique_variations.append(v)

        return unique_variations

    def _extract_content(self, page: wikipediaapi.WikipediaPage, max_paragraphs: int) -> str:
        """Extract relevant content from Wikipedia page."""
        summary = page.summary

        # Split into paragraphs and take first N
        paragraphs = [p.strip() for p in summary.split('\n') if p.strip()]
        selected = paragraphs[:max_paragraphs]

        content = '\n\n'.join(selected)

        # Limit to reasonable length (roughly 800 tokens ~ 3200 chars)
        if len(content) > 3000:
            content = content[:3000] + "..."

        return content

    def _calculate_relevance(self, query: str, title: str) -> float:
        """Calculate simple relevance score based on query-title match."""
        query_words = set(query.lower().split())
        title_words = set(title.lower().split())

        if not query_words:
            return 0.0

        overlap = len(query_words & title_words)
        return min(1.0, overlap / len(query_words))

    def get_evidence(self, claim: str) -> Optional[str]:
        """
        Get evidence text for a specific claim.

        Args:
            claim: The factual claim to verify

        Returns:
            Evidence text if found, None otherwise
        """
        result = self.search(claim)
        if result.get('found'):
            source_info = f"[Source: Wikipedia - {result.get('title')}]"
            return f"{source_info}\n{result.get('content')}"
        return None
