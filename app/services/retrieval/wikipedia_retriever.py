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
        Strategy:
        1. Full query (sometimes works for exact article titles)
        2. Named entities: year + acronym + noun combos ("2022 FIFA World Cup")
        3. Capitalized proper nouns ("Argentina", "France")
        4. Acronyms ("FIFA", "NATO", "NASA")

        Args:
            query: A claim like "The 2022 FIFA World Cup was won by Argentina"

        Returns:
            List of search terms to try
        """
        terms = []

        STOP_WORDS = {"The", "This", "That", "These", "Those", "Its", "His",
                       "Her", "Our", "Their", "Was", "Were", "Has", "Had",
                       "Are", "Not", "And", "But", "For", "With"}

        # Extract multi-word entities: sequences of capitalized/acronym words
        # with optional year prefix. Matches "2022 FIFA World Cup", "United Nations"
        entities = re.findall(
            r'(?:\d{4}\s+)?(?:[A-Z][a-zA-Z]*\s+)*[A-Z][a-zA-Z]*', query
        )
        for entity in entities:
            entity = entity.strip()
            if entity not in terms and len(entity) > 2 and entity not in STOP_WORDS:
                terms.append(entity)

        # Sort entities: multi-word first (more specific = better Wikipedia match)
        terms.sort(key=lambda t: len(t.split()), reverse=True)

        # Extract individual capitalized words (proper nouns)
        capitalized = re.findall(r'\b[A-Z][a-z]+\b', query)
        for term in capitalized:
            if term not in terms and len(term) > 2 and term not in STOP_WORDS:
                terms.append(term)

        # Extract acronyms (all-caps words, 2+ chars)
        acronyms = re.findall(r'\b[A-Z]{2,}\b', query)
        for acr in acronyms:
            if acr not in terms:
                terms.append(acr)

        return terms if terms else [query]

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

                # Use full summary (Wikipedia summaries are usually 1-3k chars)
                content = summary[:3000]

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
