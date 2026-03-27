"""
Evidence Aggregator - Layer 3
Deduplicates, ranks, and trims evidence to fit context windows.
"""

from app.core.logging import get_logger
from app.core.config import get_settings

logger = get_logger(__name__)


class EvidenceAggregator:
    """
    Aggregates evidence from multiple sources.
    
    Operations:
    1. Deduplication - remove duplicate snippets
    2. Ranking - prioritize most relevant evidence
    3. Trimming - fit within token budget (~800 tokens)
    4. Formatting - clean markup, proper citations
    """
    
    def __init__(self):
        """Initialize aggregator."""
        settings = get_settings()
        self.max_tokens = settings.max_evidence_tokens
    
    def deduplicate(self, evidence_list: list[str]) -> list[str]:
        """
        Remove duplicate evidence snippets.
        
        TODO: Implement deduplication:
        - Exact match removal
        - Fuzzy similarity matching (optional)
        
        Args:
            evidence_list: Raw evidence from all sources
            
        Returns:
            Deduplicated evidence list
        """
        logger.info(f"Deduplicating {len(evidence_list)} evidence items")
        
        # TODO: Implement
        return evidence_list
    
    def rank_evidence(self, evidence_list: list[str]) -> list[str]:
        """
        Rank evidence by relevance.
        
        TODO: Implement ranking:
        - Prioritize Wikipedia > SerpAPI
        - Shorter, clearer snippets first
        - Remove generic boilerplate
        
        Args:
            evidence_list: Deduplicated evidence
            
        Returns:
            Ranked evidence list (best first)
        """
        logger.info(f"Ranking {len(evidence_list)} evidence items")
        
        # TODO: Implement
        return evidence_list
    
    def trim_to_budget(self, evidence_text: str) -> str:
        """
        Trim evidence to fit within token budget.
        
        Keeps most relevant info first, drops less important content.
        Rough estimate: 1 token ≈ 4 characters
        
        Args:
            evidence_text: Combined evidence text
            
        Returns:
            Trimmed evidence within token budget
        """
        estimated_tokens = len(evidence_text) // 4
        
        if estimated_tokens <= self.max_tokens:
            logger.info(f"Evidence within budget: {estimated_tokens}/{self.max_tokens} tokens")
            return evidence_text
        
        logger.warning(f"Trimming evidence: {estimated_tokens} → {self.max_tokens} tokens")
        
        # TODO: Implement smart trimming that preserves key info
        char_limit = self.max_tokens * 4
        return evidence_text[:char_limit]
    
    def aggregate(self, evidence_list: list[str]) -> str:
        """
        Full aggregation pipeline.
        
        Args:
            evidence_list: Raw evidence from all sources
            
        Returns:
            Final aggregated, cleaned evidence text
        """
        if not evidence_list:
            logger.info("No evidence to aggregate")
            return ""
        
        deduped = self.deduplicate(evidence_list)
        ranked = self.rank_evidence(deduped)
        combined = "\n\n".join(ranked)
        trimmed = self.trim_to_budget(combined)
        
        logger.info(f"Aggregated evidence: {len(trimmed)} chars")
        return trimmed
