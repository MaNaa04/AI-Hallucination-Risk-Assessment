"""
Main Verify Route - Layer 1
API Gateway endpoint for hallucination detection.
POST /verify - Entry point for verification requests.

Async upgrades (Task 1 + Task 2):
- SourceRouter, LLMJudge, and EvidenceAggregator are singletons on app.state.
- Full verify result is cached in Redis (key = SHA-256 of question+answer).
  Cache hit short-circuits the entire pipeline and returns in <5ms.

Security upgrades (Task 2):
- JWT bearer authentication via get_current_user dependency (HTTPBearer).
- User-scoped rate limiting: 20 requests/minute per user_id (not per IP).
- History records written asynchronously via BackgroundTasks so the API
  response is returned immediately without blocking on MongoDB I/O.

IMPORTANT — Redis cache key contract:
  The verify cache key is ``verify_{SHA-256(question + answer)}``.
  It is intentionally GLOBAL across all users to maximise cache-hit rates.
  user_id is NOT injected into this key.
"""

import time
import uuid
import hashlib
from datetime import datetime, timezone
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from app.api.dependencies import get_current_user
from app.core.limiter import limiter
from app.core.logging import get_logger
from app.core.cache import get_cached, set_cached
from app.db.mongo import UserHistoryRepository
from app.models.history import UserHistoryRecord
from app.models.request import VerifyRequest
from app.models.response import VerifyResponse, JudgeResponse
from app.services.preprocessing.query_preprocessor import QueryPreprocessor
from app.services.analytics.tracker import AnalyticsTracker, VerificationEvent

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["verification"])

# ── Claim-aware cache TTLs ────────────────────────────────────────────────────
# Different query types have different shelf lives. A fact about Einstein is
# stable for years; a claim about today's stock price expires in minutes.
_QUERY_TYPE_TTL: dict[str, int] = {
    "encyclopedic":        604800,  # 7 days  — historical/stable facts
    "numeric_statistical": 86400,   # 24 hours — stats updated daily/weekly
    "recent_event":        3600,    # 1 hour  — news and current events
    "opinion_subjective":  1800,    # 30 min  — subjective, low cache value
}
_DEFAULT_VERIFY_TTL: int = 3600    # 1 hour fallback for unknown query types


# ── Background task: async history persistence ────────────────────────────────

async def _write_history(
    db,
    user_id: str,
    request_id: str,
    question: str,
    score: int,
    verdict: str,
    cache_hit: bool,
) -> None:
    """
    Persist a single UserHistoryRecord to MongoDB.

    Executed by FastAPI's BackgroundTasks *after* the response has been sent
    to the client, so the API latency is not affected by DB write time.

    Silently swallows all exceptions — a failed history write must never
    surface as an API error (the pipeline result was already returned).

    Args:
        db:         AsyncIOMotorDatabase handle from app.state.db.
        user_id:    JWT sub claim — the record's owner.
        request_id: UUID string from the pipeline VerifyResponse.
        question:   Original question text.
        score:      Hallucination risk score (0-100).
        verdict:    User-facing verdict string.
        cache_hit:  Whether the result was served from the global Redis cache.
    """
    if db is None:
        logger.debug("MongoDB not available — skipping history write")
        return
    try:
        record = UserHistoryRecord(
            user_id=user_id,
            request_id=uuid.UUID(request_id),
            question=question,
            score=score,
            verdict=verdict,
            cache_hit=cache_hit,
            timestamp=datetime.now(timezone.utc),
        )
        repo = UserHistoryRepository(db)
        inserted_id = await repo.insert(record.to_mongo_doc())
        logger.debug(
            f"History record saved — user={user_id!r} request_id={request_id} "
            f"_id={inserted_id}"
        )
    except Exception as exc:
        # Non-fatal: log and continue.  The client already received their response.
        logger.warning(f"History write failed (non-fatal): {exc}")


# ── Main verify endpoint ───────────────────────────────────────────────────────

@router.post("/verify", response_model=VerifyResponse)
@limiter.limit("20/minute")
async def verify(
    request: Request,
    body: VerifyRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user),
) -> VerifyResponse:
    """
    Verify if an AI answer contains hallucinations.
    Accuracy-first pipeline: may take 10-15 seconds for thorough verification.

    Requires:
        Authorization: Bearer <jwt-token> header.
        Rate limit: 20 requests per minute per user (HTTP 429 when exceeded).

    Singletons (source_router, judge, aggregator) are pulled from app.state
    to avoid per-request construction overhead and to share the pooled
    httpx.AsyncClient across all concurrent verify calls.

    After the response is built, a BackgroundTask asynchronously writes the
    result to MongoDB so the client receives the answer without any DB latency.
    """
    request_id = str(uuid.uuid4())
    pipeline_start = time.perf_counter()

    logger.info(
        f"[{request_id}] Verification request received | "
        f"user={user_id!r} "
        f"question_len={len(body.question)} answer_len={len(body.answer)}"
    )

    # ── Layer 0 — Full-pipeline cache check ──────────────────────────────────
    # Key = SHA-256(question + answer) — deterministic, collision-resistant.
    # GLOBAL across all users — user_id is intentionally NOT included here.
    # A cache hit short-circuits all 4 layers and returns in <5ms.
    _raw_verify_key = (
        hashlib.sha256(
            (body.question + body.answer).encode("utf-8")
        ).hexdigest()
    )
    verify_cache_key = f"verify_{_raw_verify_key}"

    cached_response = await get_cached(verify_cache_key)
    if cached_response is not None:
        logger.info(f"[{request_id}] Cache HIT — returning cached result")
        # Override cache_hit=True — the stored dict has False from when it was
        # first computed. We flip it here so Dev 4 can identify cached results.
        cached_response["cache_hit"] = True
        final_response = VerifyResponse(**cached_response)

        # Still write history for cache hits — the user's audit trail should
        # record every request they made, cached or not.
        background_tasks.add_task(
            _write_history,
            db=request.app.state.db,
            user_id=user_id,
            request_id=request_id,
            question=body.question,
            score=final_response.score,
            verdict=final_response.verdict,
            cache_hit=True,
        )
        return final_response

    # ── Pull singletons from app.state ────────────────────────────────────────
    source_router = request.app.state.source_router
    judge = request.app.state.judge
    aggregator = request.app.state.aggregator

    # ── Layer 2 — Query Preprocessing (Full LLM Triplet Extraction) ──────────
    step_start = time.perf_counter()
    preprocessing_ms = 0
    try:
        # Always use the full LLM-based preprocessing for accurate claim extraction.
        # The regex fast-path was bypassing LLM triplet extraction and producing
        # weak entity strings that failed to retrieve meaningful evidence.
        processed = await QueryPreprocessor.preprocess_async(body.question, body.answer)
        preprocessing_ms = int((time.perf_counter() - step_start) * 1000)
        logger.info(
            f"[{request_id}] Preprocess complete ({preprocessing_ms}ms) | "
            f"claims={len(processed.extracted_claims)}"
        )
    except Exception as e:
        preprocessing_ms = int((time.perf_counter() - step_start) * 1000)
        logger.error(f"[{request_id}] Preprocessing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query preprocessing failed: {str(e)}")

    # ── Layer 3 — Evidence Retrieval (Parallel via singleton SourceRouter) ───
    evidence_map = {}
    step_start = time.perf_counter()
    retrieval_ms = 0
    try:
        # Singleton router shares the pooled http client — no new client per request
        evidence_map = await source_router.retrieve_evidence(
            processed.extracted_claims,
            processed.query_type,
        )
        retrieval_ms = int((time.perf_counter() - step_start) * 1000)
        logger.info(
            f"[{request_id}] Retrieval complete ({retrieval_ms}ms) | "
            f"sources={len(evidence_map)}"
        )
    except Exception as e:
        retrieval_ms = int((time.perf_counter() - step_start) * 1000)
        logger.warning(
            f"[{request_id}] Retrieval failed, continuing empty: {e}", exc_info=True
        )
        evidence_map = {}

    # ── Layer 3 — Evidence Aggregation ───────────────────────────────────────
    aggregated_evidence = ""
    try:
        evidence_list = list(evidence_map.values()) if evidence_map else []
        aggregated_evidence = aggregator.aggregate(evidence_list)
    except Exception as e:
        logger.warning(f"[{request_id}] Aggregation failed: {e}")
        aggregated_evidence = ""

    # ── Layer 4 — LLM Judge ──────────────────────────────────────────────────
    step_start = time.perf_counter()
    judge_ms = 0
    _judge_failed = False  # Track error fallback so we don't cache stale verdicts
    try:
        judge_response = await judge.judge(
            body.question,
            body.answer,
            aggregated_evidence,
        )
        judge_ms = int((time.perf_counter() - step_start) * 1000)
        logger.info(
            f"[{request_id}] Judge complete ({judge_ms}ms) | "
            f"score={judge_response.score} verdict={judge_response.verdict}"
        )
    except Exception as e:
        judge_ms = int((time.perf_counter() - step_start) * 1000)
        _judge_failed = True
        logger.error(
            f"[{request_id}] LLM judge failed ({judge_ms}ms), "
            f"returning neutral verdict: {e}",
            exc_info=True,
        )
        judge_response = JudgeResponse(
            score=50,
            verdict="unverifiable",
            explanation="Verification could not be completed due to service error.",
            flag=False,
        )

    # ── Layer 5 — Response Building ──────────────────────────────────────────
    processing_time_ms = int((time.perf_counter() - pipeline_start) * 1000)
    sources = list(evidence_map.keys()) if evidence_map else None

    debug_info = {
        "claims_extracted": processed.extracted_claims,
        "evidence_found": bool(aggregated_evidence),
        "evidence_snippets": evidence_map,
        "query_type": processed.query_type,
    }

    final_response = VerifyResponse.from_judge_response(
        judge_resp=judge_response,
        sources=sources,
        request_id=request_id,
        processing_time_ms=processing_time_ms,
        debug=debug_info,
    )

    # ── Layer 5b — Cache the completed result ─────────────────────────────────
    # TTL is claim-aware:
    #   - Error fallbacks     → 60s   (self-evict quickly so next call retries)
    #   - recent_event        → 1h    (news changes fast)
    #   - encyclopedic        → 7d    (stable historical facts)
    #   - numeric_statistical → 24h   (stats update daily)
    #   - opinion_subjective  → 30min (low cache value)
    #   - unknown             → 1h    (safe default)
    try:
        if _judge_failed:
            cache_ttl = 60
        else:
            cache_ttl = _QUERY_TYPE_TTL.get(processed.query_type, _DEFAULT_VERIFY_TTL)

        await set_cached(verify_cache_key, final_response.model_dump(), ttl=cache_ttl)

        if _judge_failed:
            logger.debug(
                f"[{request_id}] Error fallback cached with 60s TTL (will self-evict)"
            )
        else:
            logger.info(
                f"[{request_id}] Result cached | "
                f"query_type={processed.query_type} ttl={cache_ttl}s"
            )
    except Exception as e:
        logger.warning(f"[{request_id}] Cache store failed (non-fatal): {e}")

    # ── Analytics Tracking ───────────────────────────────────────────────────
    try:
        tracker = AnalyticsTracker()
        tracker.record(VerificationEvent(
            request_id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            question_preview=body.question[:80],
            answer_preview=body.answer[:120],
            score=final_response.score,
            verdict=final_response.verdict,
            sources_used=sources or [],
            processing_time_ms=processing_time_ms,
            claims_count=len(processed.extracted_claims),
            evidence_chars=len(aggregated_evidence),
            provider=getattr(judge, "provider", ""),
            query_type=processed.query_type,
            sentences_found=processed.sentences_found,
            factual_sentences=processed.factual_sentences,
            preprocessing_time_ms=preprocessing_ms,
            retrieval_time_ms=retrieval_ms,
            judge_time_ms=judge_ms,
        ))
    except Exception as e:
        logger.warning(f"[{request_id}] Analytics tracking failed: {e}")

    # ── Background: persist per-user history to MongoDB ──────────────────────
    # This fires AFTER the response has been sent — zero latency impact.
    background_tasks.add_task(
        _write_history,
        db=request.app.state.db,
        user_id=user_id,
        request_id=request_id,
        question=body.question,
        score=final_response.score,
        verdict=final_response.verdict,
        cache_hit=False,
    )

    logger.info(
        f"[{request_id}] Verify pipeline complete ({processing_time_ms}ms) | "
        f"user={user_id!r} score={final_response.score} verdict={final_response.verdict}"
    )
    return final_response


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "hallucination-detection"}
