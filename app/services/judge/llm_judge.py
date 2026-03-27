"""
LLM Judge - Layer 4
Evidence-grounded fact verification using Groq (FAST & FREE).
"""

import json
import re
from typing import Optional
from openai import OpenAI

from app.core.logging import get_logger
from app.core.config import get_settings
from app.models.response import JudgeResponse

logger = get_logger(__name__)


class LLMJudge:
    """
    Uses Groq API to verify answers against evidence.
    Groq is OpenAI-compatible and extremely fast!
    """

    def __init__(self):
        """Initialize judge with Groq client."""
        settings = get_settings()
        self.api_key = settings.groq_api_key
        self.model_name = settings.groq_model

        self.client = None

        if self.api_key:
            try:
                # Groq uses OpenAI-compatible API
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url="https://api.groq.com/openai/v1"
                )
                logger.info(f"Groq initialized with model: {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to initialize Groq: {e}")

    @staticmethod
    def build_system_prompt() -> str:
        """Build system prompt for the judge."""
        return """You are a fact-verification assistant. Assess if AI-generated answers are factually accurate based SOLELY on provided evidence.

RULES:
1. Only use information from EVIDENCE section
2. If evidence doesn't cover claim → "unverifiable"
3. Cite specific evidence
4. Score conservatively

SCORING:
- 85-100: Fully verified by evidence
- 70-84: Mostly verified
- 50-69: Partially verified
- 30-49: Poorly supported
- 0-29: Contradicted or false

Always respond in valid JSON format."""

    @staticmethod
    def build_user_prompt(question: str, answer: str, evidence: str) -> str:
        """Build user prompt with question, answer, and evidence."""

        if not evidence or not evidence.strip():
            evidence = "[No evidence retrieved]"

        return f"""Verify this AI-generated answer using ONLY the provided evidence.

QUESTION: {question}

ANSWER TO VERIFY: {answer}

EVIDENCE FROM TRUSTED SOURCES:
{evidence}

Respond with JSON containing exactly these fields:
{{
    "score": <integer 0-100>,
    "verdict": "<verified | likely_hallucination | unverifiable>",
    "explanation": "<1-2 sentences explaining assessment with evidence references>",
    "flag": <true if score < 60, false otherwise>
}}"""

    def _parse_json_response(self, content: str) -> Optional[dict]:
        """Parse JSON from LLM response."""
        if not content:
            return None

        content = content.strip()

        # Direct JSON parse
        try:
            return json.loads(content)
        except:
            pass

        # Extract from markdown code block
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass

        # Extract raw JSON object
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass

        return None

    def _rule_based_fallback(self, question: str, answer: str, evidence: str) -> JudgeResponse:
        """Fallback scoring when API is unavailable."""
        logger.info("Using rule-based fallback")

        if not evidence or not evidence.strip():
            return JudgeResponse(
                score=50,
                verdict="unverifiable",
                explanation="No evidence available.",
                flag=False
            )

        # Simple keyword overlap
        answer_words = set(answer.lower().split())
        evidence_words = set(evidence.lower().split())

        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'of', 'in', 'on', 'at', 'to', 'for'}
        answer_words -= stop_words
        evidence_words -= stop_words

        if not answer_words:
            return JudgeResponse(score=50, verdict="unverifiable", explanation="Cannot analyze.", flag=False)

        overlap = len(answer_words & evidence_words)
        overlap_ratio = overlap / len(answer_words)
        score = min(100, int(overlap_ratio * 120))

        if score >= 70:
            verdict = "verified"
            explanation = f"Keywords match evidence ({int(overlap_ratio*100)}% overlap). Verified."
        elif score >= 40:
            verdict = "unverifiable"
            explanation = f"Partial match ({int(overlap_ratio*100)}% overlap). Manual check recommended."
        else:
            verdict = "likely_hallucination"
            explanation = f"Low match ({int(overlap_ratio*100)}% overlap). Not supported."

        return JudgeResponse(
            score=score,
            verdict=verdict,
            explanation=explanation,
            flag=score < 60
        )

    def judge(self, question: str, answer: str, evidence: str) -> JudgeResponse:
        """Main judge function with Groq API."""

        # No evidence case
        if not evidence or not evidence.strip():
            return JudgeResponse(
                score=50,
                verdict="unverifiable",
                explanation="No evidence available to verify.",
                flag=False
            )

        # Try Groq if configured
        if self.client and self.api_key:
            try:
                logger.info("Calling Groq API...")

                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": self.build_system_prompt()},
                        {"role": "user", "content": self.build_user_prompt(question, answer, evidence)}
                    ],
                    temperature=0.1,
                    max_tokens=500,
                    response_format={"type": "json_object"}  # Force JSON output
                )

                content = response.choices[0].message.content
                logger.debug(f"Groq response: {content}")

                parsed = self._parse_json_response(content)

                if parsed:
                    score = max(0, min(100, int(parsed.get("score", 50))))
                    verdict = parsed.get("verdict", "unverifiable")

                    if verdict not in ["verified", "likely_hallucination", "unverifiable"]:
                        verdict = "unverifiable"

                    explanation = parsed.get("explanation", "No explanation.")
                    flag = bool(parsed.get("flag", score < 60))

                    logger.info(f"Groq result: {verdict} ({score})")

                    return JudgeResponse(
                        score=score,
                        verdict=verdict,
                        explanation=explanation,
                        flag=flag
                    )

            except Exception as e:
                logger.error(f"Groq API error: {e}")

        # Fallback to rule-based
        logger.warning("Groq unavailable. Using fallback.")
        return self._rule_based_fallback(question, answer, evidence)
