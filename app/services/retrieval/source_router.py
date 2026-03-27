"""
Source Router - Layer 3
Routes queries to appropriate retrievers based on query type.
"""

from typing import Literal, Optional
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
        """Initialize routers."""
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
            "encyclopedic": ["wikipedia"],
            "recent_event": ["serpapi", "wikipedia"],
            "numeric_statistical": ["wikipedia", "serpapi"],
            "opinion_subjective": [],  # Skip retrieval
        }

        sources = routing_rules.get(query_type, ["wikipedia"])
        logger.info(f"Routing query type '{query_type}' to sources: {sources}")
        return sources

    def _retrieve_from_source(self, source: str, claim: str) -> Optional[str]:
        """
        Retrieve evidence from a specific source.

        Args:
            source: Source name ('wikipedia' or 'serpapi')
            claim: The claim to search for

        Returns:
            Evidence text if found, None otherwise
        """
        try:
            if source == "wikipedia":
                return self.wikipedia.get_evidence(claim)
            elif source == "serpapi":
                return self.serpapi.get_evidence(claim)
            else:
                logger.warning(f"Unknown source: {source}")
                return None
        except Exception as e:
            logger.error(f"Error retrieving from {source}: {e}", exc_info=True)
            return None

    def retrieve_evidence(
        self, claims: list[str], query_type: str
    ) -> dict[str, str]:
        """
        Retrieve evidence for claims from appropriate sources.

        Args:
            claims: List of extracted claims
            query_type: Type of query for routing

        Returns:
            Evidence dictionary mapping source names to evidence text
        """
        sources = self.get_sources_for_query_type(query_type)
        evidence_map = {}

        if not sources:
            logger.info("No sources to query (opinion/subjective query)")
            return evidence_map

        if not claims:
            logger.warning("No claims to search for")
            return evidence_map

        logger.info(f"Retrieving evidence for {len(claims)} claims from {sources}")

        for source in sources:
            source_evidence = []

            for claim in claims:
                logger.info(f"Searching {source} for claim: {claim[:50]}...")
                evidence = self._retrieve_from_source(source, claim)

                if evidence:
                    source_evidence.append(evidence)
                    logger.info(f"Found evidence from {source} for claim")

            if source_evidence:
                # Combine evidence from all claims for this source
                evidence_map[source] = "\n\n---\n\n".join(source_evidence)
                logger.info(f"Total evidence from {source}: {len(evidence_map[source])} chars")

        # Log summary
        if evidence_map:
            logger.info(f"Evidence collected from: {list(evidence_map.keys())}")
        else:
            logger.warning("No evidence found from any source")

        return evidence_map
