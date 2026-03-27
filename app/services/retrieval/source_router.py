"""
Source Router - Layer 3
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
    
    def retrieve_evidence(
        self, claims: list[str], query_type: str
    ) -> dict:
        """
        Retrieve evidence for claims from appropriate sources.
        
        TODO: Route to retrievers and aggregate results
        
        Args:
            claims: List of extracted claims
            query_type: Type of query for routing
            
        Returns:
            Evidence dictionary with source information
        """
        sources = self.get_sources_for_query_type(query_type)
        evidence_map = {}
        
        logger.info(f"Retrieving evidence for {len(claims)} claims from {sources}")
        
        # TODO: Implement retrieval logic
        # For each claim:
        #   For each source in sources:
        #     Call appropriate retriever
        #     Aggregate results
        
        return evidence_map
