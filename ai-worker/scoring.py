"""Proof scoring - the AI assist behind the 'verified data moat'.

Given a student's claim (skill or project contribution) and whatever proof they
provided, the LLM returns a 0-100 confidence score + a short justification. This
is ADVISORY ONLY: it fills the `ai_score` field and helps the mentor decide; it
never auto-verifies anything (human-in-the-loop by design).

Mounted under the `/score` prefix by `main.py`.

Location:
    E:\\campus-ai\\ai-worker\\scoring.py
"""

from typing import Literal

from fastapi import APIRouter, HTTPException, status
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from config import settings
from llm import get_chat_model
from schemas import ProofScoreRequest, ProofScoreResponse
from tracing import trace_config

router = APIRouter(prefix="/score", tags=["scoring"])


class _LLMProofScore(BaseModel):
    """Structured shape we force the LLM to return."""

    score: int = Field(ge=0, le=100)
    verdict: Literal["likely_genuine", "needs_review", "likely_weak"]
    reasoning: str


_SYSTEM_PROMPT = (
    "You are an academic proof-verification assistant for a college placement "
    "platform. A student has claimed a skill or a project contribution and "
    "attached some evidence. Assess how credible the claim is, based ONLY on "
    "the information provided. Be skeptical but fair.\n\n"
    "Scoring guidance:\n"
    "- 80-100 (likely_genuine): specific, verifiable evidence (e.g. a real repo "
    "link with relevant detail).\n"
    "- 40-79 (needs_review): plausible but thin or unverifiable evidence.\n"
    "- 0-39 (likely_weak): no real evidence, vague, or inconsistent.\n\n"
    "You are ADVISORY ONLY - a human mentor makes the final call. Never claim "
    "to have verified anything yourself. Keep reasoning to 1-2 short sentences."
)


@router.post("/proof", response_model=ProofScoreResponse)
def score_proof(payload: ProofScoreRequest) -> ProofScoreResponse:
    """Score one skill/project claim. Returns score + verdict + reasoning."""
    human = (
        f"Claim type: {payload.claim_type}\n"
        f"Title / skill: {payload.title}\n"
        f"Evidence URL: {payload.evidence_url or '(none provided)'}\n"
        f"Evidence note: {payload.evidence_note or '(none provided)'}"
    )

    model = get_chat_model().with_structured_output(_LLMProofScore)
    try:
        result = model.invoke(
            [SystemMessage(content=_SYSTEM_PROMPT), HumanMessage(content=human)],
            config=trace_config(
                "proof_score",
                claim_type=payload.claim_type,
                provider=settings.LLM_PROVIDER,
            ),
        )
    except Exception as exc:  # noqa: BLE001 - surface any provider/SDK error
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM call failed: {exc}",
        )

    return ProofScoreResponse(
        score=result.score,
        verdict=result.verdict,
        reasoning=result.reasoning,
        provider=settings.LLM_PROVIDER,
    )
