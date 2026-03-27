"""
Evidence Aggregator - Layer 3
Deduplicates, ranks, and trims evidence to fit context windows.
"""

import re
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

    # Source priority (lower = higher priority)
    SOURCE_PRIORITY = {
        "wikipedia": 1,
        "serpapi": 2,
        "web": 3,
    }

    def __init__(self):
        """Initialize aggregator."""
        settings = get_settings()
        self.max_tokens = settings.max_evidence_tokens

    def deduplicate(self, evidence_list: list[str]) -> list[str]:
        """
        Remove duplicate evidence snippets.

        Uses exact match and fuzzy similarity detection.

        Args:
            evidence_list: Raw evidence from all sources

        Returns:
            Deduplicated evidence list
        """
        if not evidence_list:
            return []

        logger.info(f"Deduplicating {len(evidence_list)} evidence items")

        seen_normalized = set()
        unique_evidence = []

        for evidence in evidence_list:
            if not evidence or not evidence.strip():
                continue

            # Normalize for comparison (lowercase, remove extra whitespace)
            normalized = self._normalize_text(evidence)

            # Check for exact duplicates
            if normalized in seen_normalized:
                logger.debug("Skipping exact duplicate")
                continue

            # Check for near-duplicates (high overlap)
            is_duplicate = False
            for seen in seen_normalized:
                if self._calculate_similarity(normalized, seen) > 0.85:
                    logger.debug("Skipping near-duplicate")
                    is_duplicate = True
                    break

            if not is_duplicate:
                seen_normalized.add(normalized)
                unique_evidence.append(evidence)

        logger.info(f"After deduplication: {len(unique_evidence)} items")
        return unique_evidence

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        # Lowercase
        text = text.lower()
        # Remove extra whitespace
        text = ' '.join(text.split())
        # Remove punctuation for comparison
        text = re.sub(r'[^\w\s]', '', text)
        return text

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple word-based Jaccard similarity."""
        words1 = set(text1.split())
        words2 = set(text2.split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    def rank_evidence(self, evidence_list: list[str]) -> list[str]:
        """
        Rank evidence by relevance and quality.

        Prioritization:
        1. Wikipedia evidence (more reliable)
        2. Shorter, clearer snippets
        3. Evidence with source citations

        Args:
            evidence_list: Deduplicated evidence

        Returns:
            Ranked evidence list (best first)
        """
        if not evidence_list:
            return []

        logger.info(f"Ranking {len(evidence_list)} evidence items")

        # Score each evidence item
        scored_evidence = []
        for evidence in evidence_list:
            score = self._calculate_quality_score(evidence)
            scored_evidence.append((score, evidence))

        # Sort by score (descending)
        scored_evidence.sort(key=lambda x: x[0], reverse=True)

        ranked = [e[1] for e in scored_evidence]
        return ranked

    def _calculate_quality_score(self, evidence: str) -> float:
        """Calculate quality score for evidence."""
        score = 50.0  # Base score

        lower_evidence = evidence.lower()

        # Source priority boost
        if "[source: wikipedia" in lower_evidence:
            score += 30
        elif "[source: google" in lower_evidence:
            score += 15

        # Penalize very short snippets
        if len(evidence) < 100:
            score -= 10

        # Penalize very long snippets (likely contains noise)
        if len(evidence) > 2000:
            score -= 15

        # Boost if contains specific facts (numbers, dates)
        if re.search(r'\b\d{4}\b', evidence):  # Year
            score += 5
        if re.search(r'\b\d+%|\$\d+|\d+\s*(million|billion|thousand)\b', evidence, re.IGNORECASE):
            score += 5

        # Penalize boilerplate
        boilerplate_phrases = [
            "click here", "read more", "subscribe", "sign up",
            "advertisement", "sponsored"
        ]
        for phrase in boilerplate_phrases:
            if phrase in lower_evidence:
                score -= 10

        return score

    def _clean_evidence(self, evidence: str) -> str:
        """Clean and format evidence text."""
        # Remove excessive newlines
        evidence = re.sub(r'\n{3,}', '\n\n', evidence)

        # Remove common boilerplate
        boilerplate_patterns = [
            r'\[edit\]',
            r'\[citation needed\]',
            r'Retrieved from .*',
            r'External links.*$',
        ]
        for pattern in boilerplate_patterns:
            evidence = re.sub(pattern, '', evidence, flags=re.IGNORECASE | re.MULTILINE)

        return evidence.strip()

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

        char_limit = self.max_tokens * 4

        # Try to cut at a paragraph boundary
        trimmed = evidence_text[:char_limit]

        # Find the last paragraph break within limit
        last_para = trimmed.rfind('\n\n')
        if last_para > char_limit * 0.7:  # Only if we keep at least 70%
            trimmed = trimmed[:last_para]

        # Add ellipsis to indicate truncation
        if len(evidence_text) > len(trimmed):
            trimmed = trimmed.rstrip() + "\n\n[Evidence truncated for context limit]"

        return trimmed

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

        # Filter out empty items
        evidence_list = [e for e in evidence_list if e and e.strip()]

        if not evidence_list:
            logger.info("No valid evidence after filtering")
            return ""

        # Pipeline
        deduped = self.deduplicate(evidence_list)
        ranked = self.rank_evidence(deduped)

        # Clean each evidence item
        cleaned = [self._clean_evidence(e) for e in ranked]

        # Combine
        combined = "\n\n---\n\n".join(cleaned)

        # Trim to budget
        trimmed = self.trim_to_budget(combined)

        logger.info(f"Aggregated evidence: {len(trimmed)} chars (~{len(trimmed)//4} tokens)")
        return trimmed
