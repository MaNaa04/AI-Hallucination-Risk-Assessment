"""
SerpAPI Retrieval - Layer 3
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
        # TODO: Install and import serpapi
        # from serpapi import GoogleSearch
        pass
    
    def search(self, query: str, max_results: int = 3) -> dict:
        """
        Search Google via SerpAPI for a claim.
        
        TODO: Implement SerpAPI search:
        1. Call SerpAPI with extracted claim
        2. Get top 3 organic search results
        3. Extract snippets and URLs
        4. Return as structured evidence
        
        Args:
            query: Search query/extracted claim
            max_results: Number of results to retrieve (typically 3)
            
        Returns:
            Dictionary with keys:
            - 'results': List of results with 'title', 'snippet', 'url'
            - 'search_metadata': timestamp, etc
            - 'found': True if results found
        """
        if not self.api_key:
            logger.warning("SerpAPI key not configured, skipping search")
            return {"found": False, "results": []}
        
        logger.info(f"Searching SerpAPI for: {query}")
        
        # TODO: Implement
        return {
            "found": False,
            "results": [],
            "search_metadata": None
        }
    
    def get_evidence(self, claim: str) -> Optional[str]:
        """
        Get evidence from web search for a specific claim.
        
        Args:
            claim: The factual claim to verify
            
        Returns:
            Combined snippets as evidence text
        """
        result = self.search(claim)
        if result.get('found') and result.get('results'):
            snippets = [r.get('snippet', '') for r in result['results']]
            return '\n'.join(snippets)
        return None
