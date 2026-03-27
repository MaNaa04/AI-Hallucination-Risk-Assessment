"""
Source Router - Layer 3C
Routes queries to appropriate retrievers based on query type.
"""

from typing import Literal
from app.core.logging import get_logger
from app.services.retrieval.wikipedia_retriever import WikipediaRetriever
from app.services.retrieval.serp_retriever import SerpAPIRetriever

logger = get_logger(__name__)


class SourceRouter:
    """
    Routes queries to appropriate retrieval sources.

    Decision logic (simple, no LLM):
    - encyclopedic → Wikipedia only
    - recent_event → SerpAPI first, fallback to Wikipedia
    - numeric_statistical → Try both
    - opinion_subjective → Skip retrieval
    """

    def __init__(self):
        """Initialize retrievers."""
        self.wikipedia = WikipediaRetriever()
        self.serpapi = SerpAPIRetriever()

    def get_sources_for_query_type(
        self, query_type: Literal["encyclopedic", "recent_event", "numeric_statistical", "opinion_subjective"]
    ) -> list[str]:
        """
        Determine which sources to query based on query type.

        Args:
            query_type: Classification of the query

        Returns:
            List of source names to query
        """
        routing_rules = {
            "encyclopedic": ["wikipedia", "serpapi"],
            "recent_event": ["serpapi", "wikipedia"],
            "numeric_statistical": ["wikipedia", "serpapi"],
            "opinion_subjective": [],  # Skip retrieval
        }

        sources = routing_rules.get(query_type, ["wikipedia"])
        logger.info(f"Routing query type '{query_type}' to sources: {sources}")
        return sources

    def _retrieve_from_source(self, source: str, claim: str) -> tuple[str, str | None]:
        """
        Retrieve evidence from a single source for a single claim.

        Args:
            source: Source name ("wikipedia" or "serpapi")
            claim: The claim to search for

        Returns:
            Tuple of (source_name, evidence_text or None)
        """
        try:
            if source == "wikipedia":
                evidence = self.wikipedia.get_evidence(claim)
                return ("Wikipedia", evidence)
            elif source == "serpapi":
                evidence = self.serpapi.get_evidence(claim)
                return ("SerpAPI", evidence)
            else:
                logger.warning(f"Unknown source: {source}")
                return (source, None)
        except Exception as e:
            logger.error(f"Retrieval from {source} failed for claim '{claim}': {e}", exc_info=True)
            return (source, None)

    def retrieve_evidence(
        self, claims: list[str], query_type: str
    ) -> dict:
        """
        Retrieve evidence for claims from appropriate sources.

        Loops through claims × sources, collects all evidence,
        handles partial failures gracefully.

        Args:
            claims: List of extracted claims
            query_type: Type of query for routing

        Returns:
            Evidence dictionary: {source_name: combined_evidence_text}
        """
        sources = self.get_sources_for_query_type(query_type)
        evidence_map: dict[str, list[str]] = {}

        if not claims:
            logger.info("No claims to retrieve evidence for")
            return {}

        if not sources:
            logger.info("No sources selected (opinion/subjective query)")
            return {}

        logger.info(f"Retrieving evidence for {len(claims)} claims from {sources}")

        for claim in claims:
            for source in sources:
                source_name, evidence = self._retrieve_from_source(source, claim)

                if evidence:
                    if source_name not in evidence_map:
                        evidence_map[source_name] = []
                    evidence_map[source_name].append(evidence)
                    logger.info(f"Got evidence from {source_name} for: {claim[:50]}...")

        # Combine evidence per source into single strings
        result = {}
        for source_name, evidence_list in evidence_map.items():
            result[source_name] = "\n\n".join(evidence_list)

        logger.info(f"Evidence collected from {len(result)} sources")
        return result
