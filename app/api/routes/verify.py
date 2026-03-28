"""
Main Verify Route - Layer 1
API Gateway endpoint for hallway hallucination detection.
POST /verify - Entry point for verification requests.
"""

import time
import uuid
import asyncio
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
    Pipeline uses async/await everywhere to hit 1000ms SLA.
    """
    request_id = str(uuid.uuid4())
    pipeline_start = time.perf_counter()
    
    logger.info(
        f"[{request_id}] Verification request received | "
        f"question_len={len(request.question)} answer_len={len(request.answer)}"
    )
    
    # ── Layer 2 — Query Preprocessing (with PRE-FETCH Fast Path) ───
    step_start = time.perf_counter()
    try:
        # Pre-fetch check: Avoid slow LLM if we can extract proper nouns via regex
        import re
        capitalized_entities = re.findall(r'\b(?:[A-Z][a-z]+\s+){1,2}[A-Z][a-z]+\b|\b[A-Z][a-z]+\b', request.answer)
        # Filter common words
        stopwords = {"The", "This", "That", "There", "When", "In", "It"}
        fast_claims = [e for e in set(capitalized_entities) if e not in stopwords and len(e) > 3]

        if fast_claims:
            from app.services.preprocessing.query_preprocessor import ProcessedQuery
            processed = ProcessedQuery(
                original_question=request.question,
                original_answer=request.answer,
                extracted_claims=fast_claims[:2], # Take top 2 entities
                query_type="encyclopedic" # Default to wiki
            )
            logger.info(f"[{request_id}] Pre-fetch Fast Path Engaged: Bypassed LLM Triplet Extraction")
        else:
            processed = await QueryPreprocessor.preprocess_async(request.question, request.answer)
            
        step_ms = int((time.perf_counter() - step_start) * 1000)
        logger.info(f"[{request_id}] Preprocess complete ({step_ms}ms) | claims={len(processed.extracted_claims)}")
    except Exception as e:
        logger.error(f"[{request_id}] Preprocessing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query preprocessing failed: {str(e)}")
    
    # ── Layer 3 — Evidence Retrieval (Parallel) ─────────────────────
    evidence_map = {}
    step_start = time.perf_counter()
    try:
        router_instance = SourceRouter()
        # Fire off retrieves concurrently
        evidence_map = await router_instance.retrieve_evidence(
            processed.extracted_claims,
            processed.query_type
        )
        step_ms = int((time.perf_counter() - step_start) * 1000)
        logger.info(f"[{request_id}] Retrieval complete ({step_ms}ms) | sources={len(evidence_map)}")
    except Exception as e:
        logger.warning(f"[{request_id}] Retrieval failed, continuing empty: {e}", exc_info=True)
        evidence_map = {}
    
    # ── Layer 3 — Evidence Aggregation ─────────────────────────────
    aggregated_evidence = ""
    try:
        evidence_list = list(evidence_map.values()) if evidence_map else []
        aggregator = EvidenceAggregator()
        aggregated_evidence = aggregator.aggregate(evidence_list)
    except Exception as e:
        logger.warning(f"[{request_id}] Aggregation failed: {e}")
        aggregated_evidence = ""
    
    # ── Layer 4 — LLM Judge ────────────────────────────────────────
    step_start = time.perf_counter()
    try:
        judge = LLMJudge()
        judge_response = await judge.judge(
            request.question,
            request.answer,
            aggregated_evidence
        )
        step_ms = int((time.perf_counter() - step_start) * 1000)
        logger.info(f"[{request_id}] Judge complete ({step_ms}ms) | score={judge_response.score}")
    except Exception as e:
        logger.error(f"[{request_id}] LLM judge failed: {e}", exc_info=True)
        judge_response = JudgeResponse(
            score=50,
            verdict="unverifiable",
            explanation="Verification could not be completed due to service error.",
            flag=False
        )
    
    # ── Layer 5 — Response Building ────────────────────────────────
    processing_time_ms = int((time.perf_counter() - pipeline_start) * 1000)
    sources = list(evidence_map.keys()) if evidence_map else None
    
    debug_info = {
        "claims_extracted": processed.extracted_claims,
        "evidence_found": bool(aggregated_evidence),
        "evidence_snippets": evidence_map,
        "query_type": processed.query_type
    }
    
    final_response = VerifyResponse.from_judge_response(
        judge_resp=judge_response,
        sources=sources,
        request_id=request_id,
        processing_time_ms=processing_time_ms,
        debug=debug_info
    )
    
    logger.info(
        f"[{request_id}] Verify pipeline complete ({processing_time_ms}ms) | "
        f"score={final_response.score} verdict={final_response.verdict}"
    )
    return final_response


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "hallucination-detection"}
