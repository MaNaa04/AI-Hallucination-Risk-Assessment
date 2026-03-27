"""
Tests for the LLM Judge (Layer 4).
All LLM API calls are mocked.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from app.services.judge.llm_judge import LLMJudge
from app.models.response import JudgeResponse


# ── Prompt Building Tests ──────────────────────────────────────────

class TestBuildJudgePrompt:
    """Tests for prompt construction."""

    def test_prompt_contains_all_inputs(self):
        prompt = LLMJudge.build_judge_prompt(
            "What is Paris?", "Paris is a city.", "Evidence here"
        )
        assert "What is Paris?" in prompt
        assert "Paris is a city." in prompt
        assert "Evidence here" in prompt

    def test_prompt_with_empty_evidence(self):
        prompt = LLMJudge.build_judge_prompt(
            "What is Paris?", "Paris is a city.", ""
        )
        assert "No evidence was retrieved" in prompt

    def test_prompt_requests_json(self):
        prompt = LLMJudge.build_judge_prompt("Q", "A", "E")
        assert "JSON" in prompt
        assert "score" in prompt
        assert "verdict" in prompt


# ── Response Parsing Tests ─────────────────────────────────────────

class TestParseJudgeResponse:
    """Tests for JSON response parsing."""

    def _make_judge(self):
        """Create a judge instance without API connection."""
        with patch("app.services.judge.llm_judge.get_settings") as mock:
            mock.return_value = MagicMock(
                llm_api_key="", llm_model="test", llm_provider="gemini"
            )
            return LLMJudge()

    def test_parse_clean_json(self):
        judge = self._make_judge()
        raw = json.dumps({
            "score": 85,
            "verdict": "verified",
            "explanation": "Evidence confirms.",
            "flag": False
        })
        result = judge._parse_judge_response(raw)
        assert result.score == 85
        assert result.verdict == "verified"

    def test_parse_json_in_code_block(self):
        judge = self._make_judge()
        raw = '```json\n{"score": 90, "verdict": "verified", "explanation": "Confirmed.", "flag": false}\n```'
        result = judge._parse_judge_response(raw)
        assert result.score == 90
        assert result.verdict == "verified"

    def test_parse_json_with_surrounding_text(self):
        judge = self._make_judge()
        raw = 'Here is my analysis:\n{"score": 30, "verdict": "likely_hallucination", "explanation": "Not supported.", "flag": true}\nThank you.'
        result = judge._parse_judge_response(raw)
        assert result.score == 30
        assert result.verdict == "likely_hallucination"

    def test_clamps_score_above_100(self):
        judge = self._make_judge()
        raw = json.dumps({"score": 150, "verdict": "verified", "explanation": "Test", "flag": False})
        result = judge._parse_judge_response(raw)
        assert result.score == 100

    def test_clamps_score_below_0(self):
        judge = self._make_judge()
        raw = json.dumps({"score": -10, "verdict": "verified", "explanation": "Test", "flag": False})
        result = judge._parse_judge_response(raw)
        assert result.score == 0

    def test_invalid_verdict_defaults(self):
        judge = self._make_judge()
        raw = json.dumps({"score": 50, "verdict": "maybe", "explanation": "Test", "flag": False})
        result = judge._parse_judge_response(raw)
        assert result.verdict == "unverifiable"

    def test_no_json_raises(self):
        judge = self._make_judge()
        with pytest.raises(ValueError):
            judge._parse_judge_response("This has no JSON at all.")


# ── Judge Method Tests ─────────────────────────────────────────────

class TestJudge:
    """Tests for the judge() method."""

    @patch("app.services.judge.llm_judge.get_settings")
    def test_no_api_key_returns_neutral(self, mock_settings):
        mock_settings.return_value = MagicMock(
            llm_api_key="", llm_model="test", llm_provider="gemini"
        )
        judge = LLMJudge()
        result = judge.judge("Q", "A", "E")

        assert result.score == 50
        assert result.verdict == "unverifiable"

    @patch("app.services.judge.llm_judge.get_settings")
    def test_placeholder_key_returns_neutral(self, mock_settings):
        mock_settings.return_value = MagicMock(
            llm_api_key="your_llm_api_key_here", llm_model="test", llm_provider="gemini"
        )
        judge = LLMJudge()
        result = judge.judge("Q", "A", "E")

        assert result.score == 50
        assert result.verdict == "unverifiable"

    @patch("app.services.judge.llm_judge.get_settings")
    def test_gemini_success(self, mock_settings):
        mock_settings.return_value = MagicMock(
            llm_api_key="real-key", llm_model="gemini-2.0-flash", llm_provider="gemini"
        )

        judge = LLMJudge()
        judge.api_key = "real-key"
        judge.provider = "gemini"

        # Mock the client's generate_content response
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "score": 85,
            "verdict": "verified",
            "explanation": "Evidence confirms the claim.",
            "flag": False
        })
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        judge.client = mock_client

        result = judge.judge("What is Paris?", "Paris is the capital.", "Paris is the capital of France.")

        assert result.score == 85
        assert result.verdict == "verified"

    @patch("app.services.judge.llm_judge.get_settings")
    def test_api_error_returns_neutral(self, mock_settings):
        mock_settings.return_value = MagicMock(
            llm_api_key="real-key", llm_model="gemini-2.0-flash", llm_provider="gemini"
        )

        judge = LLMJudge()
        judge.client = MagicMock()
        judge.provider = "gemini"
        judge.api_key = "real-key"
        judge.client.generate_content.side_effect = Exception("API timeout")

        result = judge.judge("Q", "A", "E")

        assert result.score == 50
        assert result.verdict == "unverifiable"
