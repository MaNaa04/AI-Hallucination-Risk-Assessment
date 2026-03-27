"""
Query Preprocessor - Layer 2
Extracts key factual claims from answers and determines query type.
"""

import re
from typing import Literal
from dataclasses import dataclass
from app.core.logging import get_logger
from app.core.config import get_settings

logger = get_logger(__name__)

QueryType = Literal["encyclopedic", "recent_event", "numeric_statistical", "opinion_subjective"]


@dataclass
class ProcessedQuery:
    """Result of query preprocessing."""
    original_question: str
    original_answer: str
    extracted_claims: list[str]
    query_type: QueryType


# ── Patterns for query type detection ─────────────────────────────

RECENT_EVENT_KEYWORDS = [
    "today", "yesterday", "tomorrow", "latest", "recent", "recently",
    "breaking", "news", "update", "current", "currently", "now",
    "this week", "this month", "this year", "last week", "last month",
    "2024", "2025", "2026",
]

NUMERIC_PATTERNS = [
    r"^how many\b", r"^how much\b", r"^what percentage\b",
    r"^what number\b", r"^how often\b", r"^what is the rate\b",
    r"^how long\b", r"^how old\b", r"^how far\b", r"^how tall\b",
    r"^what is the population\b", r"^how fast\b",
]

OPINION_PATTERNS = [
    r"^should\b", r"^do you think\b", r"^is it worth\b",
    r"^what do you recommend\b", r"^what's better\b", r"^what is better\b",
    r"^is it good\b", r"^is it bad\b", r"^would you\b",
    r"^what's your opinion\b", r"^what is your opinion\b",
    r"^can you suggest\b", r"^what are the pros\b",
]

# ── Patterns for filtering non-factual sentences ──────────────────

FILLER_PATTERNS = [
    r"^(in summary|in conclusion|overall|to summarize|in short)\b",
    r"^(i hope|i think|i believe|in my opinion)\b",
    r"^(let me know|feel free|if you have)\b",
    r"^(here is|here are|here's)\b",
    r"^(note that|please note|keep in mind)\b",
]

LEADING_CONNECTORS = re.compile(
    r"^(also|however|moreover|furthermore|additionally|in addition|"
    r"meanwhile|nevertheless|consequently|therefore|thus|hence|"
    r"for example|for instance|specifically|in fact|actually)[,\s]+",
    re.IGNORECASE,
)


class QueryPreprocessor:
    """
    Extracts key factual claims from AI responses and identifies query type.

    This layer helps route queries to appropriate retrievers:
    - encyclopedic → Wikipedia (historical, biographical, scientific)
    - recent_event → SerpAPI (news, current events)
    - numeric_statistical → Either (statistics, data)
    - opinion_subjective → Low priority (harder to verify)
    """

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        """
        Split text into sentences using regex.
        Handles common abbreviations (Dr., Mr., U.S., etc.).

        Args:
            text: Input text

        Returns:
            List of sentence strings
        """
        # Protect common abbreviations from being split
        protected = text
        abbreviations = ["Dr.", "Mr.", "Mrs.", "Ms.", "Prof.", "Jr.", "Sr.",
                         "U.S.", "U.K.", "U.N.", "e.g.", "i.e.", "etc.",
                         "vs.", "St.", "Mt.", "ft.", "Vol.", "No."]
        for abbr in abbreviations:
            protected = protected.replace(abbr, abbr.replace(".", "###DOT###"))

        # Split on sentence-ending punctuation followed by space or end
        sentences = re.split(r'(?<=[.!?])\s+', protected)

        # Restore abbreviation dots and clean up
        sentences = [s.replace("###DOT###", ".").strip() for s in sentences]
        return [s for s in sentences if s]

    @staticmethod
    def _is_factual_sentence(sentence: str) -> bool:
        """
        Determine if a sentence likely contains a verifiable factual claim.

        Filters out questions, very short text, opinions, and filler phrases.

        Args:
            sentence: A single sentence

        Returns:
            True if the sentence appears to be a factual claim
        """
        clean = sentence.strip()

        # Too short to be a meaningful claim
        if len(clean) < 15:
            return False

        # Questions are not claims
        if clean.endswith("?"):
            return False

        # Filter filler/opinion phrases
        lower = clean.lower()
        for pattern in FILLER_PATTERNS:
            if re.match(pattern, lower):
                return False

        return True

    @staticmethod
    def _clean_claim(sentence: str) -> str:
        """
        Clean a sentence into a concise search query.

        Strips leading connectors, trailing punctuation, and extra whitespace.

        Args:
            sentence: A factual sentence

        Returns:
            Cleaned search query string
        """
        claim = sentence.strip()

        # Remove leading connectors (e.g., "However, ...", "Also, ...")
        claim = LEADING_CONNECTORS.sub("", claim)

        # Remove trailing punctuation
        claim = claim.rstrip(".!;:")

        # Normalize whitespace
        claim = re.sub(r'\s+', ' ', claim).strip()

        return claim

    @staticmethod
    def extract_claims(answer: str, max_claims: int = 3) -> list[str]:
        """
        Extract key factual claims from the answer.

        Uses heuristic approach:
        1. Split answer into sentences
        2. Filter out non-factual sentences
        3. Clean into concise search queries
        4. Return up to max_claims results

        Args:
            answer: The AI-generated answer
            max_claims: Maximum number of claims to extract

        Returns:
            List of extracted claims as search queries
        """
        settings = get_settings()
        max_claims = min(max_claims, settings.max_claims_per_request)

        logger.info(f"Extracting claims from answer (max: {max_claims})")

        if not answer or len(answer.strip()) < 10:
            logger.warning("Answer too short for claim extraction")
            return []

        # Step 1: Split into sentences
        sentences = QueryPreprocessor._split_sentences(answer)
        logger.info(f"Split answer into {len(sentences)} sentences")

        # Step 2: Filter for factual sentences
        factual = [s for s in sentences if QueryPreprocessor._is_factual_sentence(s)]
        logger.info(f"Found {len(factual)} factual sentences")

        # Step 3: Clean into search queries
        claims = [QueryPreprocessor._clean_claim(s) for s in factual]

        # Remove empty claims after cleaning
        claims = [c for c in claims if len(c) >= 10]

        # Step 4: Return top claims (prioritize longer, more specific sentences)
        claims.sort(key=len, reverse=True)
        result = claims[:max_claims]

        logger.info(f"Extracted {len(result)} claims")
        return result

    @staticmethod
    def determine_query_type(question: str) -> QueryType:
        """
        Determine the type of query for routing to appropriate retrievers.

        Uses keyword pattern matching:
        - recent_event: time-related keywords, year references
        - numeric_statistical: "how many", "how much", "percentage"
        - opinion_subjective: "should", "recommend", "better"
        - encyclopedic: default fallback for factual questions

        Args:
            question: The original question

        Returns:
            Query type classification
        """
        logger.info("Determining query type")

        lower = question.lower().strip()

        # Check for opinion/subjective first (most specific)
        for pattern in OPINION_PATTERNS:
            if re.match(pattern, lower):
                logger.info("Query type: opinion_subjective")
                return "opinion_subjective"

        # Check for numeric/statistical
        for pattern in NUMERIC_PATTERNS:
            if re.match(pattern, lower):
                logger.info("Query type: numeric_statistical")
                return "numeric_statistical"

        # Check for recent events
        for keyword in RECENT_EVENT_KEYWORDS:
            if keyword in lower:
                logger.info("Query type: recent_event")
                return "recent_event"

        # Default: encyclopedic
        logger.info("Query type: encyclopedic")
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

        return ProcessedQuery(
            original_question=question,
            original_answer=answer,
            extracted_claims=claims,
            query_type=query_type
        )
