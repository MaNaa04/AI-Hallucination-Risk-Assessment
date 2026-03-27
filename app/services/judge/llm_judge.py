"""
LLM Judge - Layer 4
Evidence-grounded fact verification using an LLM.
Supports: Google Gemini (default/free), OpenAI.
"""

import json
import re
from typing import Optional
from app.core.logging import get_logger
from app.core.config import get_settings
from app.models.response import JudgeResponse

logger = get_logger(__name__)


class LLMJudge:
    """
    Uses an LLM to verify answers against evidence.

    This is NOT a pure GPT-as-Judge approach.
    Instead, it's evidence-grounded:
    1. We provide the question, answer, AND evidence
    2. The LLM judges based ONLY on the evidence
    3. This reduces hallucination in the judge itself

    Supported providers (set LLM_PROVIDER in .env):
    - "gemini" (default) — Google Gemini, free tier available
    - "openai" — OpenAI GPT-4/3.5
    """

    def __init__(self):
        """Initialize judge with LLM client."""
        settings = get_settings()
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model
        self.provider = settings.llm_provider
        self.client = None

        if not self.api_key or self.api_key in ("your_llm_api_key_here", ""):
            logger.warning("LLM API key not configured")
            return

        try:
            if self.provider == "gemini":
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                logger.info(f"Initialized Gemini judge with model: {self.model}")

            elif self.provider == "openai":
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
                logger.info(f"Initialized OpenAI judge with model: {self.model}")

            elif self.provider == "grok":
                from openai import OpenAI
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url="https://api.x.ai/v1",
                )
                logger.info(f"Initialized Grok/xAI judge with model: {self.model}")

            elif self.provider == "groq":
                from openai import OpenAI
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url="https://api.groq.com/openai/v1",
                )
                logger.info(f"Initialized Groq judge with model: {self.model}")

            else:
                logger.error(f"Unknown LLM provider: {self.provider}")

        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}", exc_info=True)
            self.client = None

    @staticmethod
    def build_judge_prompt(question: str, answer: str, evidence: str) -> str:
        """
        Build the judge prompt for evidence-grounded evaluation.

        Args:
            question: Original question
            answer: AI-generated answer
            evidence: Retrieved evidence from sources

        Returns:
            Formatted prompt for the LLM
        """
        if not evidence or evidence.strip() == "":
            evidence = "No evidence was retrieved for this claim."

        prompt = f"""You are a fact-verification assistant.
You will be given a question, an AI-generated answer, and retrieved evidence from trusted sources.
Your job is to assess whether the answer is factually accurate based solely on the evidence provided.

QUESTION: {question}

ANSWER: {answer}

EVIDENCE: {evidence}

Respond in JSON format with exactly these fields:
{{
    "score": <integer 0-100, where 0=definitely hallucination, 100=fully verified>,
    "verdict": "<one of: verified, likely_hallucination, unverifiable>",
    "explanation": "<1-2 sentences explaining your assessment, grounded in the evidence>",
    "flag": <true if score < 60, false otherwise>
}}

Only use information from the evidence provided. If the evidence is empty or doesn't cover the claim, use 'unverifiable' with score around 50."""

        return prompt

    def _call_gemini(self, prompt: str) -> str:
        """Call Google Gemini API using google.genai SDK."""
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )
        return response.text

    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a fact-verification assistant. Always respond in valid JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=300,
        )
        return response.choices[0].message.content

    def _parse_judge_response(self, raw_text: str) -> JudgeResponse:
        """
        Parse LLM response text into JudgeResponse.

        Handles JSON extraction from markdown code blocks and raw text.

        Args:
            raw_text: Raw LLM output

        Returns:
            Parsed JudgeResponse
        """
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', raw_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1).strip()
        else:
            # Try to find raw JSON object
            json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                raise ValueError(f"No JSON found in LLM response: {raw_text[:200]}")

        data = json.loads(json_str)

        # Validate and clamp score
        score = int(data.get("score", 50))
        score = max(0, min(100, score))

        # Validate verdict
        verdict = data.get("verdict", "unverifiable")
        valid_verdicts = ("verified", "likely_hallucination", "unverifiable")
        if verdict not in valid_verdicts:
            verdict = "unverifiable"

        return JudgeResponse(
            score=score,
            verdict=verdict,
            explanation=data.get("explanation", "No explanation provided."),
            flag=data.get("flag", score < 60),
        )

    @staticmethod
    def _heuristic_judge(question: str, answer: str, evidence: str) -> JudgeResponse:
        """
        Fallback: heuristic keyword-overlap judge.

        Used when LLM API is unavailable (quota, network, no key).
        Compares answer keywords against evidence to estimate accuracy.
        """
        if not evidence or evidence.strip() == "":
            return JudgeResponse(
                score=50,
                verdict="unverifiable",
                explanation="No evidence available to verify this claim.",
                flag=False,
            )

        # Extract meaningful words (>3 chars, lowercased)
        import re as _re
        answer_words = set(
            w for w in _re.findall(r'\b\w+\b', answer.lower())
            if len(w) > 3
        )
        evidence_lower = evidence.lower()

        if not answer_words:
            return JudgeResponse(
                score=50,
                verdict="unverifiable",
                explanation="Answer too short to analyze.",
                flag=False,
            )

        # Count how many answer keywords appear in the evidence
        matches = sum(1 for w in answer_words if w in evidence_lower)
        overlap = matches / len(answer_words)

        # Map overlap to score (0.0 → 30, 0.5 → 65, 1.0 → 92)
        score = int(30 + (overlap * 62))
        score = max(0, min(100, score))

        if score >= 70:
            verdict = "verified"
            explanation = f"Heuristic check: {matches}/{len(answer_words)} key terms found in evidence."
        elif score >= 45:
            verdict = "unverifiable"
            explanation = f"Heuristic check: partial match — {matches}/{len(answer_words)} key terms found."
        else:
            verdict = "likely_hallucination"
            explanation = f"Heuristic check: low match — only {matches}/{len(answer_words)} key terms found in evidence."

        return JudgeResponse(
            score=score,
            verdict=verdict,
            explanation=explanation,
            flag=score < 60,
        )

    def judge(self, question: str, answer: str, evidence: str) -> JudgeResponse:
        """
        Judge the answer based on evidence.

        1. Try LLM API (Gemini or OpenAI)
        2. On any failure, fall back to heuristic keyword-overlap judge

        Args:
            question: Original question
            answer: AI-generated answer
            evidence: Aggregated evidence

        Returns:
            Judge's assessment as JudgeResponse
        """
        if not self.api_key or self.api_key in ("your_llm_api_key_here", ""):
            logger.warning("LLM API key not configured, using heuristic judge")
            return self._heuristic_judge(question, answer, evidence)

        if not self.client:
            logger.error("LLM client not initialized, using heuristic judge")
            return self._heuristic_judge(question, answer, evidence)

        prompt = self.build_judge_prompt(question, answer, evidence)
        logger.info(f"Calling {self.provider} judge (model: {self.model})")

        try:
            if self.provider == "gemini":
                raw_response = self._call_gemini(prompt)
            elif self.provider in ("openai", "grok", "groq"):
                raw_response = self._call_openai(prompt)
            else:
                raise ValueError(f"Unknown provider: {self.provider}")

            logger.info(f"LLM response received ({len(raw_response)} chars)")
            return self._parse_judge_response(raw_response)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}", exc_info=True)
            return self._heuristic_judge(question, answer, evidence)
        except Exception as e:
            logger.error(f"LLM judge call failed: {e}, falling back to heuristic judge")
            return self._heuristic_judge(question, answer, evidence)

