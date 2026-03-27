"""
Main Verify Route - Layer 1
API Gateway endpoint for hallucination detection.
POST /verify - Entry point for verification requests.
"""

from fastapi import APIRouter, HTTPException
from app.core.logging import get_logger
from app.models.request import VerifyRequest
from app.models.response import VerifyResponse
from app.services.preprocessing.query_preprocessor import QueryPreprocessor
from app.services.retrieval.source_router import SourceRouter
from app.services.retrieval.evidence_aggregator import EvidenceAggregator
from app.services.judge.llm_judge import LLMJudge

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["verification"])


@router.post("/verify", response_model=VerifyResponse)
async def verify(request: VerifyRequest) -> VerifyResponse:
    """
    Verify if an AI answer contains hallucinations.
    
    Pipeline:
    1. [Layer 2] Preprocess query: extract claims & determine type
    2. [Layer 3] Retrieve evidence: Wikipedia, SerpAPI, etc.
    3. [Layer 3] Aggregate evidence: deduplicate, rank, trim
    4. [Layer 4] Judge: evaluate with evidence via LLM
    5. [Layer 5] Format response: apply thresholds, add sources
    
    Args:
        request: VerifyRequest with question and answer
        
    Returns:
        VerifyResponse with score, verdict, explanation
        
    Raises:
        HTTPException: On validation or processing errors
    """
    try:
        logger.info(f"Verification request received")
        
        # TODO: Layer 1 - Input already validated by Pydantic
        
        # Layer 2 - Query Preprocessing
        logger.info("Step 1: Preprocessing query")
        processed = QueryPreprocessor.preprocess(request.question, request.answer)
        logger.info(f"Extracted {len(processed.extracted_claims)} claims, type: {processed.query_type}")
        
        # Layer 3 - Retrieval
        logger.info("Step 2: Retrieving evidence")
        router_instance = SourceRouter()
        evidence_map = router_instance.retrieve_evidence(
            processed.extracted_claims,
            processed.query_type
        )
        
        # Layer 3 - Evidence Aggregation
        logger.info("Step 3: Aggregating evidence")
        evidence_list = list(evidence_map.values()) if evidence_map else []
        aggregator = EvidenceAggregator()
        aggregated_evidence = aggregator.aggregate(evidence_list)
        
        # Layer 4 - LLM Judge
        logger.info("Step 4: Judging with LLM")
        judge = LLMJudge()
        judge_response = judge.judge(
            request.question,
            request.answer,
            aggregated_evidence
        )
        
        # Layer 5 - Response Building
        logger.info("Step 5: Building response")
        sources = list(evidence_map.keys()) if evidence_map else None
        final_response = VerifyResponse.from_judge_response(judge_response, sources)
        
        logger.info(f"Verification complete: score={final_response.score}, verdict={final_response.verdict}")
        return final_response
        
    except Exception as e:
        logger.error(f"Verification failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Verification pipeline failed: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "hallucination-detection"}
