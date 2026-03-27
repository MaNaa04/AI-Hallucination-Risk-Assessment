"""
Tests for the /api/verify endpoint (Layer 1).
Uses FastAPI TestClient with mocked downstream services.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.models.response import JudgeResponse
from app.services.preprocessing.query_preprocessor import ProcessedQuery
from main import app

client = TestClient(app)


# ── Fixtures ───────────────────────────────────────────────────────

VALID_PAYLOAD = {
    "question": "What is the capital of France?",
    "answer": "The capital of France is Paris, located along the Seine River."
}

MOCK_PROCESSED = ProcessedQuery(
    original_question="What is the capital of France?",
    original_answer="The capital of France is Paris, located along the Seine River.",
    extracted_claims=["Paris is capital of France"],
    query_type="encyclopedic"
)

MOCK_EVIDENCE_MAP = {
    "Wikipedia": "Paris is the capital and largest city of France."
}

MOCK_JUDGE_RESPONSE = JudgeResponse(
    score=90,
    verdict="verified",
    explanation="Evidence confirms Paris is the capital of France.",
    flag=False
)


# ── Success Path ───────────────────────────────────────────────────

class TestVerifyEndpointSuccess:
    """Tests for the happy path of /api/verify."""

    @patch("app.api.routes.verify.LLMJudge")
    @patch("app.api.routes.verify.EvidenceAggregator")
    @patch("app.api.routes.verify.SourceRouter")
    @patch("app.api.routes.verify.QueryPreprocessor")
    def test_full_pipeline_success(
        self, mock_preprocessor, mock_router_cls, mock_aggregator_cls, mock_judge_cls
    ):
        # Setup mocks
        mock_preprocessor.preprocess.return_value = MOCK_PROCESSED

        mock_router = MagicMock()
        mock_router.retrieve_evidence.return_value = MOCK_EVIDENCE_MAP
        mock_router_cls.return_value = mock_router

        mock_aggregator = MagicMock()
        mock_aggregator.aggregate.return_value = "Paris is the capital and largest city of France."
        mock_aggregator_cls.return_value = mock_aggregator

        mock_judge = MagicMock()
        mock_judge.judge.return_value = MOCK_JUDGE_RESPONSE
        mock_judge_cls.return_value = mock_judge

        response = client.post("/api/verify", json=VALID_PAYLOAD)

        assert response.status_code == 200
        data = response.json()
        assert data["score"] == 90
        assert data["verdict"] == "accurate"
        assert data["explanation"] == "Evidence confirms Paris is the capital of France."
        assert data["flag"] is False
        assert data["sources_used"] == ["Wikipedia"]
        assert "request_id" in data
        assert "processing_time_ms" in data


# ── Validation Errors ─────────────────────────────────────────────

class TestVerifyEndpointValidation:
    """Tests for input validation (Pydantic handles these)."""

    def test_missing_question(self):
        response = client.post("/api/verify", json={
            "answer": "Paris is the capital of France."
        })
        assert response.status_code == 422

    def test_missing_answer(self):
        response = client.post("/api/verify", json={
            "question": "What is the capital of France?"
        })
        assert response.status_code == 422

    def test_question_too_short(self):
        response = client.post("/api/verify", json={
            "question": "Hi",
            "answer": "Paris is the capital of France."
        })
        assert response.status_code == 422

    def test_answer_too_short(self):
        response = client.post("/api/verify", json={
            "question": "What is the capital?",
            "answer": "Yes"
        })
        assert response.status_code == 422

    def test_empty_body(self):
        response = client.post("/api/verify", json={})
        assert response.status_code == 422


# ── Graceful Degradation ──────────────────────────────────────────

class TestVerifyEndpointDegradation:
    """Tests for graceful degradation when services fail."""

    @patch("app.api.routes.verify.LLMJudge")
    @patch("app.api.routes.verify.EvidenceAggregator")
    @patch("app.api.routes.verify.SourceRouter")
    @patch("app.api.routes.verify.QueryPreprocessor")
    def test_retrieval_failure_degrades_gracefully(
        self, mock_preprocessor, mock_router_cls, mock_aggregator_cls, mock_judge_cls
    ):
        """When retrieval fails, pipeline continues with empty evidence."""
        mock_preprocessor.preprocess.return_value = MOCK_PROCESSED

        mock_router = MagicMock()
        mock_router.retrieve_evidence.side_effect = Exception("Wikipedia API down")
        mock_router_cls.return_value = mock_router

        # Aggregator should still be called (with empty list)
        mock_aggregator = MagicMock()
        mock_aggregator.aggregate.return_value = ""
        mock_aggregator_cls.return_value = mock_aggregator

        mock_judge = MagicMock()
        mock_judge.judge.return_value = JudgeResponse(
            score=50, verdict="unverifiable",
            explanation="No evidence available.", flag=False
        )
        mock_judge_cls.return_value = mock_judge

        response = client.post("/api/verify", json=VALID_PAYLOAD)
        assert response.status_code == 200
        data = response.json()
        assert data["verdict"] == "uncertain"  # score 50 → uncertain

    @patch("app.api.routes.verify.LLMJudge")
    @patch("app.api.routes.verify.EvidenceAggregator")
    @patch("app.api.routes.verify.SourceRouter")
    @patch("app.api.routes.verify.QueryPreprocessor")
    def test_judge_failure_returns_neutral(
        self, mock_preprocessor, mock_router_cls, mock_aggregator_cls, mock_judge_cls
    ):
        """When LLM judge fails, return neutral score."""
        mock_preprocessor.preprocess.return_value = MOCK_PROCESSED

        mock_router = MagicMock()
        mock_router.retrieve_evidence.return_value = MOCK_EVIDENCE_MAP
        mock_router_cls.return_value = mock_router

        mock_aggregator = MagicMock()
        mock_aggregator.aggregate.return_value = "Some evidence"
        mock_aggregator_cls.return_value = mock_aggregator

        mock_judge = MagicMock()
        mock_judge.judge.side_effect = Exception("LLM API timeout")
        mock_judge_cls.return_value = mock_judge

        response = client.post("/api/verify", json=VALID_PAYLOAD)
        assert response.status_code == 200
        data = response.json()
        assert data["score"] == 50
        assert data["verdict"] == "uncertain"

    @patch("app.api.routes.verify.QueryPreprocessor")
    def test_preprocessing_failure_returns_500(self, mock_preprocessor):
        """When preprocessing fails, return 500 (can't continue without claims)."""
        mock_preprocessor.preprocess.side_effect = Exception("NLP model failed")

        response = client.post("/api/verify", json=VALID_PAYLOAD)
        assert response.status_code == 500


# ── Health Check ──────────────────────────────────────────────────

class TestHealthCheck:
    """Tests for /api/health endpoint."""

    def test_health_check(self):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "hallucination-detection"
