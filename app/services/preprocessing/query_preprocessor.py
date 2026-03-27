"""
Query Preprocessor - Layer 2
Extracts key factual claims from answers and determines query type.
"""

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
    
    @staticmethod
    def extract_claims(answer: str, max_claims: int = 3) -> list[str]:
        """
        Extract key factual claims from the answer.
        
        TODO: Implement claim extraction using:
        - Small LLM call OR
        - Regex + heuristics (start simple, add NLP later)
        
        Prompt: "Extract 2-3 most verifiable factual claims from this answer as short search queries."
        
        Args:
            answer: The AI-generated answer
            max_claims: Maximum number of claims to extract
            
        Returns:
            List of extracted claims as search queries
        """
        # TODO: Implement
        logger.info(f"Extracting claims from answer (max: {max_claims})")
        return []
    
    @staticmethod
    def determine_query_type(question: str) -> QueryType:
        """
        Determine the type of query for routing to appropriate retrievers.
        
        TODO: Implement routing logic:
        - "When was X born?" → encyclopedic
        - "What happened yesterday?" → recent_event
        - "How many..." → numeric_statistical
        - "Should I..." → opinion_subjective
        
        Args:
            question: The original question
            
        Returns:
            Query type classification
        """
        # TODO: Implement
        logger.info("Determining query type")
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
