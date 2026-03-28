"""
Wikipedia Retrieval - Layer 3A
Retrieves factual/encyclopedic information from Wikipedia API via async HTTPX.
"""

import re
import asyncio
import httpx
from typing import Optional
from app.core.logging import get_logger
from app.core.cache import get_cached, set_cached

logger = get_logger(__name__)


class WikipediaRetriever:
    """
    Retrieves evidence from Wikipedia for encyclopedic claims.
    Uses generous timeouts (10s) to maximise evidence retrieval for accuracy.
    """

    def __init__(self):
        """Initialize Wikipedia retriever."""
        self.base_url = "https://en.wikipedia.org/w/api.php"
        # Accuracy-first: allow up to 10 seconds for Wikipedia to respond
        self.timeout = 10.0

    @staticmethod
    def _extract_search_terms(query: str) -> list[str]:
        """
        Extract search terms (Primary exact term -> Broader fuzzy keywords).
        """
        terms = []
        STOP_WORDS = {"The", "This", "That", "These", "Those", "Its", "His",
                       "Her", "Our", "Their", "Was", "Were", "Has", "Had",
                       "Are", "Not", "And", "But", "For", "With", "In"}

        # 1. Primary: exact phrase stripping punctuation
        clean_query = re.sub(r'[^\w\s]', '', query).strip()
        if clean_query:
            terms.append(clean_query)

        # 2. Extract multi-word entities (Fuzzy Keyword search)
        entities = re.findall(
            r'(?:\d{4}\s+)?(?:[A-Z][a-zA-Z]*\s+)*[A-Z][a-zA-Z]*', query
        )
        for entity in entities:
            entity = entity.strip()
            if entity not in terms and len(entity) > 2 and entity not in STOP_WORDS:
                terms.append(entity)
                
        # 3. Last resort fuzzy keyword: Capitalized proper nouns
        capitalized = re.findall(r'\b[A-Z][a-z]+\b', query)
        for term in capitalized:
            if term not in terms and len(term) > 2 and term not in STOP_WORDS:
                terms.append(term)
                
        # Make sure we have something
        if not terms:
            terms = [clean_query]

        return terms

    def _extract_top_snippets(self, text: str, query: str, top_n: int = 5) -> str:
        """
        Slice evidence to Top N snippets/sentences ranked by relevance.
        Returns more context so the LLM judge can make accurate decisions.
        """
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 15]
        
        if not sentences:
            return ""
            
        # Score sentences by keyword overlap with query
        query_words = set(query.lower().split())
        scored = []
        for s in sentences:
            s_lower = s.lower()
            score = sum(1 for w in query_words if w in s_lower)
            scored.append((score, s))
            
        # Sort by score desc, take top N
        scored.sort(key=lambda x: x[0], reverse=True)
        top = [s[1] for s in scored[:top_n]]
        return " ... ".join(top)

    async def search(self, query: str) -> dict:
        """
        Search Wikipedia for a claim using `httpx` async calls.
        """
        cache_key = f"wiki_{query}"
        cached = get_cached(cache_key)
        if cached:
            logger.info(f"Wiki cache hit for: {query}")
            return cached

        search_terms = self._extract_search_terms(query)
        logger.info(f"Wiki search terms (Primary -> Fuzzy): {search_terms}")

        async with httpx.AsyncClient(timeout=self.timeout, headers={"User-Agent": "AIHallucinationDetector/1.0", "Accept": "application/json"}) as client:
            for term in search_terms:
                try:
                    # 1. First, search for the page title
                    search_params = {
                        "action": "query",
                        "list": "search",
                        "srsearch": term,
                        "utf8": "",
                        "format": "json",
                        "srlimit": 1
                    }
                    search_res = await client.get(self.base_url, params=search_params)
                    search_data = search_res.json()
                    
                    search_list = search_data.get("query", {}).get("search", [])
                    if not search_list:
                        logger.info(f"Wiki fuzzy miss for term: {term}")
                        continue
                        
                    title = search_list[0]["title"]
                    
                    # 2. Fetch the page extract — larger budget for accuracy
                    extract_params = {
                        "action": "query",
                        "prop": "extracts",
                        "exchars": 2000,
                        "titles": title,
                        "explaintext": 1,
                        "format": "json"
                    }
                    ext_res = await client.get(self.base_url, params=extract_params)
                    ext_data = ext_res.json()
                    
                    pages = ext_data.get("query", {}).get("pages", {})
                    if not pages or "-1" in pages:
                        continue
                        
                    page_id = list(pages.keys())[0]
                    content = pages[page_id].get("extract", "")
                    
                    if not content:
                        continue
                        
                    # Extract top 5 most-relevant snippets for rich evidence
                    snippets = self._extract_top_snippets(content, query, top_n=5)
                    if not snippets:
                        snippets = content[:600]  # fallback — more chars

                    result = {
                        "title": title,
                        "content": snippets,
                        "url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                        "found": True,
                    }
                    
                    # Cache successful result
                    set_cached(cache_key, result)
                    logger.info(f"Wiki Hit: '{title}' via '{term}'")
                    return result

                except httpx.TimeoutException:
                    logger.error(f"Wiki timeout (>10s) for term: {term} — trying next term")
                    # Try next term instead of aborting everything
                    continue
                except Exception as e:
                    logger.error(f"Wiki API error: {e}")
                    continue

        # Nothing found
        failed = {"title": None, "content": None, "url": None, "found": False}
        set_cached(cache_key, failed)
        return failed

    async def get_evidence(self, claim: str) -> Optional[str]:
        """Get evidence text for a claim."""
        result = await self.search(claim)
        if result.get("found"):
            return result.get("content")
        return None
