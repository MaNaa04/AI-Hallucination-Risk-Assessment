"""
Response models for API output formatting.
Layer 5: Response Builder
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal


class JudgeResponse(BaseModel):
    """
    Judgment output from the LLM Judge.
    
    Attributes:
        score: Hallucination risk score (0-100)
        verdict: Classification of the answer
        explanation: Evidence-grounded reasoning
        flag: Whether the response needs attention
    """
    score: int = Field(
        ..., 
        ge=0, 
        le=100,
        description="Hallucination risk score"
    )
    verdict: Literal["verified", "likely_hallucination", "unverifiable"] = Field(
        ...,
        description="Classification verdict"
    )
    explanation: str = Field(
        ...,
        description="1-2 sentence explanation grounded in evidence"
    )
    flag: bool = Field(
        ...,
        description="True if score < 60 (needs attention)"
    )


class VerifyResponse(BaseModel):
    """
    Complete response from the /verify endpoint.
    
    Maps score ranges to user-friendly verdicts:
    - 75-100: ✅ Likely accurate
    - 40-74: ⚠️ Uncertain, verify
    - 0-39: 🚩 High hallucination risk
    """
    score: int = Field(
        ..., 
        ge=0, 
        le=100,
        description="Hallucination risk score (0-100)"
    )
    verdict: Literal["accurate", "uncertain", "hallucination"] = Field(
        ...,
        description="User-friendly verdict"
    )
    explanation: str = Field(
        ...,
        description="Explanation of the verdict"
    )
    flag: bool = Field(
        ...,
        description="Red flag if high hallucination risk"
    )
    sources_used: Optional[list[str]] = Field(
        default=None,
        description="Which sources provided evidence (Wikipedia, SerpAPI, etc.)"
    )
    
    @staticmethod
    def from_judge_response(judge_resp: JudgeResponse, sources: Optional[list[str]] = None) -> "VerifyResponse":
        """
        Convert LLM Judge response to user-facing response.
        
        Args:
            judge_resp: Raw judge response
            sources: Sources used for evidence retrieval
            
        Returns:
            Formatted response with user-friendly verdict
        """
        # Map judge verdict to user-friendly verdict based on score
        if judge_resp.score >= 75:
            verdict = "accurate"
        elif judge_resp.score >= 40:
            verdict = "uncertain"
        else:
            verdict = "hallucination"
        
        return VerifyResponse(
            score=judge_resp.score,
            verdict=verdict,
            explanation=judge_resp.explanation,
            flag=judge_resp.flag,
            sources_used=sources
        )
    
    class Config:
        json_schema_extra = {
            "example": {
                "score": 85,
                "verdict": "accurate",
                "explanation": "Verified against Wikipedia. Paris is indeed the capital of France.",
                "flag": False,
                "sources_used": ["Wikipedia"]
            }
        }
