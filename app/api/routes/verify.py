"""
Main Verify Route - Layer 1
API Gateway endpoint for hallucination detection.
POST /verify - Entry point for verification requests.
"""

import time
import uuid
from fastapi import APIRouter, HTTPException
from app.core.logging import get_logger
from app.models.request import VerifyRequest
from app.models.response import VerifyResponse, JudgeResponse
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
    request_id = str(uuid.uuid4())
    pipeline_start = time.time()
    
    logger.info(
        f"[{request_id}] Verification request received | "
        f"question_len={len(request.question)} answer_len={len(request.answer)}"
    )
    
    # ── Layer 2 — Query Preprocessing ──────────────────────────────
    step_start = time.time()
    try:
        logger.info(f"[{request_id}] Step 1: Preprocessing query")
        processed = QueryPreprocessor.preprocess(request.question, request.answer)
        step_ms = int((time.time() - step_start) * 1000)
        logger.info(
            f"[{request_id}] Step 1 complete ({step_ms}ms) | "
            f"claims={len(processed.extracted_claims)} type={processed.query_type}"
        )
    except Exception as e:
        logger.error(f"[{request_id}] Preprocessing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Query preprocessing failed: {str(e)}"
        )
    
    # ── Layer 3 — Evidence Retrieval ───────────────────────────────
    evidence_map = {}
    step_start = time.time()
    try:
        logger.info(f"[{request_id}] Step 2: Retrieving evidence")
        router_instance = SourceRouter()
        evidence_map = router_instance.retrieve_evidence(
            processed.extracted_claims,
            processed.query_type
        )
        step_ms = int((time.time() - step_start) * 1000)
        logger.info(
            f"[{request_id}] Step 2 complete ({step_ms}ms) | "
            f"sources_found={len(evidence_map)}"
        )
    except Exception as e:
        step_ms = int((time.time() - step_start) * 1000)
        logger.warning(
            f"[{request_id}] Evidence retrieval failed ({step_ms}ms), "
            f"continuing with empty evidence: {e}",
            exc_info=True
        )
        evidence_map = {}
    
    # ── Layer 3 — Evidence Aggregation ─────────────────────────────
    aggregated_evidence = ""
    step_start = time.time()
    try:
        logger.info(f"[{request_id}] Step 3: Aggregating evidence")
        evidence_list = list(evidence_map.values()) if evidence_map else []
        aggregator = EvidenceAggregator()
        aggregated_evidence = aggregator.aggregate(evidence_list)
        step_ms = int((time.time() - step_start) * 1000)
        logger.info(
            f"[{request_id}] Step 3 complete ({step_ms}ms) | "
            f"evidence_chars={len(aggregated_evidence)}"
        )
    except Exception as e:
        step_ms = int((time.time() - step_start) * 1000)
        logger.warning(
            f"[{request_id}] Evidence aggregation failed ({step_ms}ms), "
            f"continuing with empty evidence: {e}",
            exc_info=True
        )
        aggregated_evidence = ""
    
    # ── Layer 4 — LLM Judge ────────────────────────────────────────
    step_start = time.time()
    try:
        logger.info(f"[{request_id}] Step 4: Judging with LLM")
        judge = LLMJudge()
        judge_response = judge.judge(
            request.question,
            request.answer,
            aggregated_evidence
        )
        step_ms = int((time.time() - step_start) * 1000)
        logger.info(
            f"[{request_id}] Step 4 complete ({step_ms}ms) | "
            f"judge_score={judge_response.score} judge_verdict={judge_response.verdict}"
        )
    except Exception as e:
        step_ms = int((time.time() - step_start) * 1000)
        logger.error(
            f"[{request_id}] LLM judge failed ({step_ms}ms), "
            f"returning neutral verdict: {e}",
            exc_info=True
        )
        judge_response = JudgeResponse(
            score=50,
            verdict="unverifiable",
            explanation="Verification could not be completed due to a service error.",
            flag=False
        )
    
    # ── Layer 5 — Response Building ────────────────────────────────
    processing_time_ms = int((time.time() - pipeline_start) * 1000)
    sources = list(evidence_map.keys()) if evidence_map else None
    
    final_response = VerifyResponse.from_judge_response(
        judge_response,
        sources=sources,
        request_id=request_id,
        processing_time_ms=processing_time_ms,
    )
    
    logger.info(
        f"[{request_id}] Verification complete ({processing_time_ms}ms) | "
        f"score={final_response.score} verdict={final_response.verdict}"
    )
    return final_response


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "hallucination-detection"}
