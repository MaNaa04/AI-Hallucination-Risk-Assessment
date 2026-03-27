"""
Query Preprocessor - Layer 2
Extracts key factual claims from answers and determines query type.
"""

import re
from typing import Literal
from dataclasses import dataclass
from app.core.logging import get_logger

logger = get_logger(__name__)

QueryType = Literal["encyclopedic", "recent_event", "numeric_statistical", "opinion_subjective"]


@dataclass
class ProcessedQuery:
    """Result of query preprocessing."""
    original_question: str
    original_answer: str
    extracted_claims: list[str]
    query_type: QueryType


class QueryPreprocessor:
    """
    Extracts key factual claims from AI responses and identifies query type.

    This layer helps route queries to appropriate retrievers:
    - encyclopedic → Wikipedia (historical, biographical, scientific)
    - recent_event → SerpAPI (news, current events)
    - numeric_statistical → Either (statistics, data)
    - opinion_subjective → Low priority (harder to verify)
    """

    # Patterns for query type detection
    RECENT_EVENT_PATTERNS = [
        r'\b(today|yesterday|this week|this month|this year|202[3-9]|recent|latest|current|now)\b',
        r'\b(news|announced|released|launched|happened|trending)\b',
    ]

    OPINION_PATTERNS = [
        r'^(should|could|would|might|do you think|what do you think|is it good|is it bad)',
        r'\b(opinion|believe|feel|think|prefer|recommend|best|worst)\b',
    ]

    NUMERIC_PATTERNS = [
        r'\b(how many|how much|what percentage|what number|statistics|data|count|total)\b',
        r'\b(\d+%|\d+\s*(million|billion|thousand))\b',
    ]

    @staticmethod
    def extract_claims(answer: str, max_claims: int = 3) -> list[str]:
        """
        Extract key factual claims from the answer using heuristics.

        Strategy:
        1. Split answer into sentences
        2. Filter out opinion/filler sentences
        3. Extract key fact-containing sentences
        4. Convert to searchable queries

        Args:
            answer: The AI-generated answer
            max_claims: Maximum number of claims to extract

        Returns:
            List of extracted claims as search queries
        """
        logger.info(f"Extracting claims from answer (max: {max_claims})")

        # Split into sentences
        sentences = re.split(r'[.!?]+', answer)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]

        if not sentences:
            # Fallback: use the whole answer as a single claim
            return [answer[:200]] if answer else []

        claims = []
        for sentence in sentences:
            # Skip opinion-like sentences
            if QueryPreprocessor._is_opinion_sentence(sentence):
                continue

            # Skip filler sentences
            if QueryPreprocessor._is_filler_sentence(sentence):
                continue

            # Extract the core claim
            claim = QueryPreprocessor._extract_core_claim(sentence)
            if claim and len(claim) > 10:
                claims.append(claim)

            if len(claims) >= max_claims:
                break

        # If no claims extracted, use first sentence
        if not claims and sentences:
            claims = [QueryPreprocessor._extract_core_claim(sentences[0])]

        logger.info(f"Extracted {len(claims)} claims")
        return claims[:max_claims]

    @staticmethod
    def _is_opinion_sentence(sentence: str) -> bool:
        """Check if sentence is opinion-based."""
        opinion_indicators = [
            'i think', 'i believe', 'in my opinion', 'probably', 'maybe',
            'could be', 'might be', 'it seems', 'apparently'
        ]
        lower = sentence.lower()
        return any(indicator in lower for indicator in opinion_indicators)

    @staticmethod
    def _is_filler_sentence(sentence: str) -> bool:
        """Check if sentence is filler/intro text."""
        filler_patterns = [
            r'^(yes|no|sure|okay|certainly|absolutely)',
            r'^(here is|here are|the answer is|to answer)',
            r'^(let me|i will|i can|i\'ll)',
        ]
        lower = sentence.lower().strip()
        return any(re.match(p, lower) for p in filler_patterns)

    @staticmethod
    def _extract_core_claim(sentence: str) -> str:
        """Extract the core factual claim from a sentence."""
        # Remove common prefixes
        prefixes_to_remove = [
            r'^(the\s+)?answer\s+is\s+that\s+',
            r'^(it\s+is\s+)?(important|interesting|notable)\s+to\s+note\s+that\s+',
            r'^(basically|essentially|simply|actually)\s*,?\s*',
        ]

        claim = sentence
        for pattern in prefixes_to_remove:
            claim = re.sub(pattern, '', claim, flags=re.IGNORECASE)

        # Clean up whitespace
        claim = ' '.join(claim.split())

        # Limit length for search
        if len(claim) > 150:
            # Try to cut at a comma or natural break
            if ',' in claim[:150]:
                claim = claim[:claim.rfind(',', 0, 150)]
            else:
                claim = claim[:150]

        return claim.strip()

    @staticmethod
    def determine_query_type(question: str) -> QueryType:
        """
        Determine the type of query for routing to appropriate retrievers.

        Args:
            question: The original question

        Returns:
            Query type classification
        """
        logger.info("Determining query type")
        lower_question = question.lower()

        # Check for recent event patterns
        for pattern in QueryPreprocessor.RECENT_EVENT_PATTERNS:
            if re.search(pattern, lower_question, re.IGNORECASE):
                logger.info("Query type: recent_event")
                return "recent_event"

        # Check for opinion patterns
        for pattern in QueryPreprocessor.OPINION_PATTERNS:
            if re.search(pattern, lower_question, re.IGNORECASE):
                logger.info("Query type: opinion_subjective")
                return "opinion_subjective"

        # Check for numeric/statistical patterns
        for pattern in QueryPreprocessor.NUMERIC_PATTERNS:
            if re.search(pattern, lower_question, re.IGNORECASE):
                logger.info("Query type: numeric_statistical")
                return "numeric_statistical"

        # Default to encyclopedic
        logger.info("Query type: encyclopedic (default)")
        return "encyclopedic"

    @staticmethod
    def preprocess(question: str, answer: str) -> ProcessedQuery:
        """
        Full preprocessing pipeline.

        Args:
            question: Original question
            answer: AI-generated answer

        Returns:
            Processed query with extracted claims and type
        """
        claims = QueryPreprocessor.extract_claims(answer)
        query_type = QueryPreprocessor.determine_query_type(question)

        # If no claims extracted, use question + answer summary
        if not claims:
            claims = [f"{question} {answer[:100]}"]

        return ProcessedQuery(
            original_question=question,
            original_answer=answer,
            extracted_claims=claims,
            query_type=query_type
        )
