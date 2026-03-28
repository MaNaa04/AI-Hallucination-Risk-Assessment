"""
Source Router - Layer 3C
Routes queries to appropriate retrievers based on query type using asyncio.gather.
"""

import asyncio
from typing import Literal
from app.core.logging import get_logger
from app.services.retrieval.wikipedia_retriever import WikipediaRetriever
from app.services.retrieval.serp_retriever import SerpAPIRetriever

logger = get_logger(__name__)


class SourceRouter:
    """
    Routes queries to appropriate retrieval sources concurrently via asyncio.gather.
    """

    def __init__(self):
        """Initialize retrievers."""
        self.wikipedia = WikipediaRetriever()
        self.serpapi = SerpAPIRetriever()

    def get_sources_for_query_type(
        self, query_type: str
    ) -> list[str]:
        """Determine which sources to query."""
        routing_rules = {
            "encyclopedic": ["wikipedia", "serpapi"],
            "recent_event": ["serpapi", "wikipedia"],
            "numeric_statistical": ["wikipedia", "serpapi"],
            "opinion_subjective": [],  # Skip retrieval
        }

        sources = routing_rules.get(query_type, ["wikipedia"])
        return sources

    async def _retrieve_from_source(self, source: str, claim: str) -> tuple[str, str | None]:
        """Retrieve evidence from a single source."""
        try:
            if source == "wikipedia":
                evidence = await self.wikipedia.get_evidence(claim)
                return ("Wikipedia", evidence)
            elif source == "serpapi":
                evidence = await self.serpapi.get_evidence(claim)
                return ("SerpAPI", evidence)
            else:
                return (source, None)
        except Exception as e:
            logger.error(f"Async retrieval from {source} failed for '{claim}': {e}")
            return (source, None)

    async def retrieve_evidence(
        self, claims: list[str], query_type: str
    ) -> dict:
        """
        Parallel fetch evidence for all claims.
        """
        sources = self.get_sources_for_query_type(query_type)
        if not claims or not sources:
            return {}

        logger.info(f"Parallel fetching: {len(claims)} claims × {len(sources)} sources")

        tasks = []
        # Span all combinations into event loop
        for claim in claims:
            for source in sources:
                task = asyncio.create_task(self._retrieve_from_source(source, claim))
                tasks.append(task)

        # Fire simultaneously
        results = await asyncio.gather(*tasks)

        # Recombine evidence
        evidence_map: dict[str, list[str]] = {}
        for source_name, evidence in results:
            if evidence:
                if source_name not in evidence_map:
                    evidence_map[source_name] = []
                evidence_map[source_name].append(evidence)

        # Join per source
        final_map = {}
        for source_name, evidence_list in evidence_map.items():
            final_map[source_name] = "\n\n".join(evidence_list)

        return final_map
