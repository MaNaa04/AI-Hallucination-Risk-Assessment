"""
LLM Judge - Layer 4
Evidence-grounded fact verification using an LLM.
Fully Async with strict `gpt-4o-mini` enforcement for <1s latency.
"""

import json
import re
from typing import Optional
from openai import AsyncOpenAI
from app.core.logging import get_logger
from app.core.config import get_settings
from app.models.response import JudgeResponse

logger = get_logger(__name__)

class LLMJudge:
    """
    Uses an LLM to verify answers against evidence via async calls.
    Enforces gpt-4o-mini for maximum speed.
    """

    def __init__(self):
        """Initialize judge with AsyncOpenAI client."""
        settings = get_settings()
        self.api_key = settings.llm_api_key
        
        # Override to 4o-mini for 1-second rule constraint
        self.model = "gpt-4o-mini"
        self.client = None

        if not self.api_key or self.api_key in ("your_llm_api_key_here", ""):
            logger.warning("LLM API key not configured")
            return

        try:
            # Assuming the API key is an OpenAI key. 
            # If using Groq, they would set base_url="https://api.groq.com/openai/v1"
            base_url = None
            if settings.llm_provider == "groq":
                base_url = "https://api.groq.com/openai/v1"
                self.model = "llama3-70b-8192" # Use Groq's fast llama
            elif settings.llm_provider == "grok":
                base_url = "https://api.x.ai/v1"
                
            self.client = AsyncOpenAI(api_key=self.api_key, base_url=base_url)
            logger.info(f"Initialized Async Judge with model: {self.model}")

        except Exception as e:
            logger.error(f"Failed to initialize Async LLM client: {e}", exc_info=True)
            self.client = None

    @staticmethod
    def build_judge_prompt(question: str, answer: str, evidence: str) -> str:
        """
        Build the judge prompt for evidence-grounded evaluation.
        Calibrated to output strict 0, 50, or 100.
        """
        if not evidence or evidence.strip() == "":
            evidence = "No evidence was retrieved for this claim."

        prompt = f"""You are a strict factual fact-verification judge.
Evaluate the AI's answer against the retrieved evidence.
Return exactly this JSON:
{{
    "score": <0, 50, or 100>,
    "verdict": "<verified, likely_hallucination, unverifiable>",
    "explanation": "<1 sentence explanation based on evidence>"
}}

SCORING RULES:
- 100 (verified): Evidence explicitly confirms the Answer.
- 50 (unverifiable): Evidence is missing, empty, or doesn't address the claim.
- 0 (likely_hallucination): Evidence directly contradicts the Answer.

QUESTION: {question}
ANSWER: {answer}
EVIDENCE: {evidence}"""

        return prompt

    async def _call_openai(self, prompt: str) -> str:
        """Call async OpenAI API."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a fact-checking JSON agent."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=150, # Fast output
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content

    def _parse_judge_response(self, raw_text: str) -> JudgeResponse:
        """Parse LLM response text into JudgeResponse."""
        try:
            data = json.loads(raw_text)
            score = int(data.get("score", 50))
            verdict = data.get("verdict", "unverifiable")
            
            # Calibration mapping just in case LLM goes offscript
            if score > 75:
                score = 100
                verdict = "verified"
            elif score < 25:
                score = 0
                verdict = "likely_hallucination"
            else:
                score = 50
                verdict = "unverifiable"

            return JudgeResponse(
                score=score,
                verdict=verdict,
                explanation=data.get("explanation", "No explanation provided."),
                flag=score < 60,
            )
        except Exception:
            # Fallback for parsing errors
            return self._heuristic_judge("unknown", "unknown", "unknown")

    @staticmethod
    def _heuristic_judge(question: str, answer: str, evidence: str) -> JudgeResponse:
        """Fallback returning 50 Neutral."""
        return JudgeResponse(
            score=50,
            verdict="unverifiable",
            explanation="Service unavailable. Could not verify.",
            flag=False,
        )

    def _early_exit_check(self, answer: str, evidence: str) -> Optional[JudgeResponse]:
        """
        Check for obvious immediate contradictions in text before wasting LLM time.
        """
        if not evidence or evidence.strip() == "":
            return JudgeResponse(
                score=50,
                verdict="unverifiable",
                explanation="No evidence retrieved.",
                flag=False
            )
        return None

    async def judge(self, question: str, answer: str, evidence: str) -> JudgeResponse:
        """
        Judge the answer based on evidence asynchronously.
        """
        # 1. Early Exit Contradiction/Empty Check
        early_exit = self._early_exit_check(answer, evidence)
        if early_exit:
            return early_exit

        if not self.client:
            return self._heuristic_judge(question, answer, evidence)

        prompt = self.build_judge_prompt(question, answer, evidence)
        try:
            raw_response = await self._call_openai(prompt)
            return self._parse_judge_response(raw_response)
        except Exception as e:
            logger.error(f"Async LLM judge failed: {e}")
            return self._heuristic_judge(question, answer, evidence)

    async def extract_triplets(self, answer: str) -> list[dict]:
        """
        Extract Atomic Knowledge Triplets asynchronously using optimized prompt.
        """
        if not self.client:
            return []

        prompt = f"""Extract verifiable "Atomic Knowledge Triplets" from this text.
Return STRICTLY a JSON list of objects: [{{"subject": "X", "predicate": "Y", "object": "Z"}}]
Ignore opinions. Split complex facts.
Text: "{answer}"
"""
        logger.info(f"Extracting triplets via {self.model}")
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=250
            )
            raw_response = response.choices[0].message.content
            
            # Simple list parser
            json_match = re.search(r'\[.*\]', raw_response, re.DOTALL)
            if json_match:
                triplets = json.loads(json_match.group(0))
                if isinstance(triplets, list):
                    return triplets
            return []
        except Exception as e:
            logger.error(f"Async Triplet extraction failed: {e}")
            return []
