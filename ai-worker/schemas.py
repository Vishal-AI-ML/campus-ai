"""Request/response schemas for the AI worker's HTTP API.

Location:
    E:\\campus-ai\\ai-worker\\schemas.py
"""

from typing import Literal

from pydantic import BaseModel, Field


class ProofScoreRequest(BaseModel):
    """A claim to assess. The backend will send a skill or a project here."""

    claim_type: Literal["skill", "project"] = "skill"
    title: str = Field(
        min_length=1,
        max_length=300,
        examples=["FastAPI"],
        description="Skill name, or project/contribution title.",
    )
    evidence_url: str | None = Field(
        default=None, examples=["https://github.com/me/campus-api"]
    )
    evidence_note: str | None = Field(
        default=None, description="Any text the student provided as proof."
    )


class ProofScoreResponse(BaseModel):
    """The worker's assessment. Advisory only - a human mentor still decides."""

    score: int = Field(ge=0, le=100, description="0-100 confidence the proof is genuine.")
    verdict: str = Field(description="likely_genuine | needs_review | likely_weak")
    reasoning: str = Field(description="Short, mentor-facing justification.")
    provider: str = Field(description="Which LLM produced this (groq/gemini).")
