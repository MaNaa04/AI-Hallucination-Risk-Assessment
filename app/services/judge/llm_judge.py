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

    def judge(self, question: str, answer: str, evidence: str) -> JudgeResponse:
        """
        Judge the answer based on evidence.

        1. Build prompt with question, answer, evidence
        2. Call LLM API (Gemini or OpenAI)
        3. Parse JSON response
        4. Return JudgeResponse

        Args:
            question: Original question
            answer: AI-generated answer
            evidence: Aggregated evidence

        Returns:
            Judge's assessment as JudgeResponse
        """
        if not self.api_key or self.api_key in ("your_llm_api_key_here", ""):
            logger.warning("LLM API key not configured, returning neutral verdict")
            return JudgeResponse(
                score=50,
                verdict="unverifiable",
                explanation="LLM judge not configured. Add LLM_API_KEY to .env file.",
                flag=False,
            )

        if not self.client:
            logger.error("LLM client not initialized")
            return JudgeResponse(
                score=50,
                verdict="unverifiable",
                explanation="LLM client initialization failed.",
                flag=False,
            )

        prompt = self.build_judge_prompt(question, answer, evidence)
        logger.info(f"Calling {self.provider} judge (model: {self.model})")

        try:
            if self.provider == "gemini":
                raw_response = self._call_gemini(prompt)
            elif self.provider == "openai":
                raw_response = self._call_openai(prompt)
            else:
                raise ValueError(f"Unknown provider: {self.provider}")

            logger.info(f"LLM response received ({len(raw_response)} chars)")
            return self._parse_judge_response(raw_response)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}", exc_info=True)
            return JudgeResponse(
                score=50,
                verdict="unverifiable",
                explanation="Failed to parse judge response.",
                flag=False,
            )
        except Exception as e:
            logger.error(f"LLM judge call failed: {e}", exc_info=True)
            return JudgeResponse(
                score=50,
                verdict="unverifiable",
                explanation=f"Judge error: {str(e)[:100]}",
                flag=False,
            )
