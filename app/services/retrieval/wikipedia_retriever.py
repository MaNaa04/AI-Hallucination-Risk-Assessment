"""
Wikipedia Retrieval - Layer 3
Retrieves factual/encyclopedic information from Wikipedia API.
"""

from typing import Optional
from app.core.logging import get_logger

logger = get_logger(__name__)


class WikipediaRetriever:
    """
    Retrieves evidence from Wikipedia for encyclopedic claims.
    
    Best for: named entities, historical facts, scientific concepts,
    biographical info, places, organizations.
    
    Tech: Use `wikipedia-api` Python library
    """
    
    def __init__(self):
        """Initialize Wikipedia retriever."""
        # TODO: Install and import wikipedia-api
        # import wikipedia
        pass
    
    def search(self, query: str, max_results: int = 2) -> dict:
        """
        Search Wikipedia for a claim.
        
        TODO: Implement Wikipedia search:
        1. Search with the extracted claim
        2. Get the top result
        3. Extract first 2 paragraphs
        4. Return as structured evidence
        
        Args:
            query: Search query/extracted claim
            max_results: Number of results to retrieve (typically 2)
            
        Returns:
            Dictionary with keys:
            - 'title': Article title
            - 'content': Extracted paragraphs
            - 'url': Wikipedia article URL
            - 'relevance_score': 0-1 confidence
        """
        logger.info(f"Searching Wikipedia for: {query}")
        
        # TODO: Implement
        return {
            "title": None,
            "content": None,
            "url": None,
            "relevance_score": 0.0,
            "found": False
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
        if result.get('found'):
            return result.get('content')
        return None
