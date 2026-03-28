"""
SerpAPI Retrieval - Layer 3B
Retrieves live web results via async HTTPX for sub-second latency.
"""

import httpx
from typing import Optional
from app.core.logging import get_logger
from app.core.config import get_settings
from app.core.cache import get_cached, set_cached

logger = get_logger(__name__)


class SerpAPIRetriever:
    """
    Retrieves evidence from Google Search via SerpAPI HTTP rest endpoint.
    Strict 600ms timeouts and fuzzy fallback search enabled.
    """

    def __init__(self):
        """Initialize SerpAPI retriever."""
        settings = get_settings()
        self.api_key = settings.serpapi_key
        self.timeout = 0.6 # Strict sub-second latency SLA

    def _fuzzy_keywords(self, query: str) -> list[str]:
        """Generate broader search terms if the strict query fails."""
        import re
        terms = [query]
        # Drop all numbers/symbols and grab capitalized proper nouns
        capitalized = re.findall(r'\b[A-Z][a-z]+\b', query)
        if capitalized:
            terms.append(" ".join(capitalized))
        
        # Simple stopword strip
        stopwords = {"the", "is", "at", "which", "on"}
        clean = " ".join([w for w in query.split() if w.lower() not in stopwords])
        if clean and clean != query:
            terms.append(clean)
            
        return terms

    async def search(self, query: str) -> dict:
        """
        Search Google using direct async httpx call to avoid blocking SDKs.
        """
        if not self.api_key or self.api_key == "your_serpapi_key_here":
            return {"found": False, "results": [], "search_metadata": None}

        cache_key = f"serp_{query}"
        cached = get_cached(cache_key)
        if cached:
            logger.info(f"SerpAPI Cache hit for: {query}")
            return cached

        logger.info(f"Searching SerpAPI for: {query[:50]}...")
        
        search_terms = self._fuzzy_keywords(query)
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for term in search_terms:
                try:
                    params = {
                        "q": term,
                        "api_key": self.api_key,
                        "engine": "google",
                        "num": 2, # Top 2 snippets ONLY
                    }
                    
                    res = await client.get("https://serpapi.com/search", params=params)
                    raw = res.json()
                    results = []

                    # Extract Knowledge Graph first
                    if "answer_box" in raw:
                        box = raw["answer_box"]
                        answer = box.get("answer") or box.get("snippet") or box.get("result")
                        if answer:
                            results.append({
                                "title": box.get("title", "Answer Box"),
                                "snippet": str(answer),
                                "url": box.get("link", ""),
                                "source": "knowledge_graph",
                            })

                    # Extract Top Organic
                    for item in raw.get("organic_results", [])[:2]:
                        if len(results) >= 2:
                            break
                        results.append({
                            "title": item.get("title", ""),
                            "snippet": item.get("snippet", ""),
                            "url": item.get("link", ""),
                            "source": "organic",
                        })

                    if results:
                        response_obj = {
                            "found": True,
                            "results": results,
                            "search_metadata": raw.get("search_metadata"),
                        }
                        set_cached(cache_key, response_obj)
                        logger.info(f"SerpAPI Hit: {len(results)} top snippets via '{term}'")
                        return response_obj
                        
                except httpx.TimeoutException:
                    logger.error(f"SerpAPI timeout (>600ms) for: {term}")
                    break # Break on first timeout to protect 1s rule
                except Exception as e:
                    logger.error(f"SerpAPI search failed: {e}")
                    continue

        failed = {"found": False, "results": [], "search_metadata": None}
        set_cached(cache_key, failed)
        return failed

    async def get_evidence(self, claim: str) -> Optional[str]:
        """Get evidence from Top 2 web search snippets."""
        result = await self.search(claim)
        if result.get("found") and result.get("results"):
            snippets = [r.get("snippet", "") for r in result["results"] if r.get("snippet")]
            # Join up to top 2 for small context
            return "\n".join(snippets[:2]) if snippets else None
        return None
