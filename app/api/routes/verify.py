"""
Main Verify Route - Layer 1
API Gateway endpoint for hallway hallucination detection.
POST /verify - Entry point for verification requests.
"""

import time
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from app.core.logging import get_logger
from app.models.request import VerifyRequest
from app.models.response import VerifyResponse, JudgeResponse
from app.services.preprocessing.query_preprocessor import QueryPreprocessor
from app.services.retrieval.source_router import SourceRouter
from app.services.retrieval.evidence_aggregator import EvidenceAggregator
from app.services.judge.llm_judge import LLMJudge
from app.services.analytics.tracker import AnalyticsTracker, VerificationEvent

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["verification"])

@router.post("/verify", response_model=VerifyResponse)
async def verify(request: VerifyRequest) -> VerifyResponse:
    """
    Verify if an AI answer contains hallucinations.
    Accuracy-first pipeline: may take 10-15 seconds for thorough verification.
    """
    request_id = str(uuid.uuid4())
    pipeline_start = time.perf_counter()
    
    logger.info(
        f"[{request_id}] Verification request received | "
        f"question_len={len(request.question)} answer_len={len(request.answer)}"
    )
    
    # ── Layer 2 — Query Preprocessing (Full LLM Triplet Extraction) ─
    step_start = time.perf_counter()
    try:
        # Always use the full LLM-based preprocessing for accurate claim extraction.
        # The regex fast-path was bypassing LLM triplet extraction and producing
        # weak entity strings that failed to retrieve meaningful evidence.
        processed = await QueryPreprocessor.preprocess_async(request.question, request.answer)
        preprocessing_ms = int((time.perf_counter() - step_start) * 1000)
        step_ms = preprocessing_ms
        logger.info(f"[{request_id}] Preprocess complete ({step_ms}ms) | claims={len(processed.extracted_claims)}")
    except Exception as e:
        preprocessing_ms = int((time.perf_counter() - step_start) * 1000)
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
        retrieval_ms = int((time.perf_counter() - step_start) * 1000)
        logger.info(f"[{request_id}] Retrieval complete ({retrieval_ms}ms) | sources={len(evidence_map)}")
    except Exception as e:
        retrieval_ms = int((time.perf_counter() - step_start) * 1000)
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
        judge_ms = int((time.time() - step_start) * 1000)
        step_ms = judge_ms
        logger.info(
            f"[{request_id}] Step 4 complete ({step_ms}ms) | "
            f"judge_score={judge_response.score} judge_verdict={judge_response.verdict}"
        )
    except Exception as e:
        judge_ms = int((time.time() - step_start) * 1000)
        step_ms = judge_ms
        logger.error(
            f"[{request_id}] LLM judge failed ({step_ms}ms), "
            f"returning neutral verdict: {e}",
            exc_info=True
        )
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
    
    # ── Analytics Tracking ─────────────────────────────────────────
    try:
        tracker = AnalyticsTracker()
        tracker.record(VerificationEvent(
            request_id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            question_preview=request.question[:80],
            answer_preview=request.answer[:120],
            score=final_response.score,
            verdict=final_response.verdict,
            sources_used=sources or [],
            processing_time_ms=processing_time_ms,
            claims_count=len(processed.extracted_claims),
            evidence_chars=len(aggregated_evidence),
            provider=getattr(judge, 'provider', ''),
            query_type=processed.query_type,
            sentences_found=processed.sentences_found,
            factual_sentences=processed.factual_sentences,
            preprocessing_time_ms=preprocessing_ms,
            retrieval_time_ms=retrieval_ms,
            judge_time_ms=judge_ms,
        ))
    except Exception as e:
        logger.warning(f"[{request_id}] Analytics tracking failed: {e}")
    
    logger.info(
        f"[{request_id}] Verify pipeline complete ({processing_time_ms}ms) | "
        f"score={final_response.score} verdict={final_response.verdict}"
    )
    return final_response


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "hallucination-detection"}
