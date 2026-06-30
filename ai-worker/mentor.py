"""AI Career Mentor - grounded chat with vector RAG.

Two sources of truth, kept strictly separate:
  1. The student's VERIFIED PROFILE (passed in by the backend) - the ONLY source
     for personal facts (their skills, projects, attendance, CGPA). The mentor
     must never claim the student has something not listed here.
  2. A GENERAL CAREER KNOWLEDGE BASE (vector-retrieved via rag.py) - used for
     advice, role expectations, interview/resume tips. Cited separately.

This keeps the 'no hallucination about the student' promise while still giving
rich, knowledgeable career guidance.

Mounted under the `/mentor` prefix by `main.py`.

Location:
    E:\\campus-ai\\ai-worker\\mentor.py
"""

from typing import Literal

from fastapi import APIRouter, HTTPException, status
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from config import settings
from llm import get_chat_model
from rag import retrieve
from tracing import trace_config

router = APIRouter(prefix="/mentor", tags=["mentor"])


# --- Schemas (local to this feature) ---------------------------------------
class MentorProject(BaseModel):
    title: str
    contribution: str | None = None


class MentorProfile(BaseModel):
    """The student's VERIFIED data - the only ground truth for personal facts."""

    verified_skills: list[str] = Field(default_factory=list)
    projects: list[MentorProject] = Field(default_factory=list)
    attendance_percentage: float | None = None
    cgpa: float | None = None


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class MentorChatRequest(BaseModel):
    profile: MentorProfile
    question: str = Field(min_length=1, max_length=2000)
    history: list[ChatTurn] = Field(default_factory=list)


class MentorChatResponse(BaseModel):
    answer: str
    provider: str


_SYSTEM_PROMPT = (
    "You are an AI Career Mentor for a college student on a placement platform. "
    "You have two sources:\n"
    "1) The student's VERIFIED PROFILE - the ONLY source for personal facts "
    "(their skills, projects, attendance, CGPA). NEVER claim the student has "
    "anything not listed there. If the profile lacks the needed info, say so "
    "honestly and tell them what to add or get verified.\n"
    "2) GENERAL CAREER KNOWLEDGE - use it for advice, role expectations, and "
    "interview/resume tips. Cite it as [source: career knowledge].\n"
    "When you refer to the student's own data, cite it as [source: verified "
    "profile]. Be concise, practical, and encouraging."
)


def _format_profile(p: MentorProfile) -> str:
    """Render the verified profile as compact text for the system prompt."""
    skills = ", ".join(p.verified_skills) if p.verified_skills else "(none verified yet)"
    if p.projects:
        projects = "; ".join(
            f"{pr.title} ({pr.contribution or 'contributor'})" for pr in p.projects
        )
    else:
        projects = "(none verified yet)"
    attendance = (
        f"{p.attendance_percentage}%"
        if p.attendance_percentage is not None
        else "(no data)"
    )
    cgpa = str(p.cgpa) if p.cgpa is not None else "(no data)"
    return (
        f"- Verified skills: {skills}\n"
        f"- Verified projects: {projects}\n"
        f"- Attendance: {attendance}\n"
        f"- CGPA: {cgpa}"
    )


@router.post("/chat", response_model=MentorChatResponse)
def mentor_chat(payload: MentorChatRequest) -> MentorChatResponse:
    """Answer a career question using the verified profile + retrieved knowledge."""
    # Vector-retrieve the most relevant career-knowledge chunks for this question.
    kb_chunks = retrieve(payload.question, k=3)
    knowledge = "\n---\n".join(kb_chunks) if kb_chunks else "(no relevant knowledge found)"

    system = (
        f"{_SYSTEM_PROMPT}\n\nSTUDENT VERIFIED PROFILE:\n"
        f"{_format_profile(payload.profile)}\n\nGENERAL CAREER KNOWLEDGE:\n"
        f"{knowledge}"
    )
    messages = [SystemMessage(content=system)]
    # Keep the last few turns for context (bounded to limit tokens).
    for turn in payload.history[-10:]:
        if turn.role == "user":
            messages.append(HumanMessage(content=turn.content))
        else:
            messages.append(AIMessage(content=turn.content))
    messages.append(HumanMessage(content=payload.question))

    try:
        result = get_chat_model().invoke(
            messages,
            config=trace_config("mentor_chat", provider=settings.LLM_PROVIDER),
        )
    except Exception as exc:  # noqa: BLE001 - surface any provider/SDK error
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM call failed: {exc}",
        )

    return MentorChatResponse(answer=str(result.content), provider=settings.LLM_PROVIDER)
