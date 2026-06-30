"""AI Resume builder + ATS scoring (AI worker).

Two LLM-backed, provider-agnostic endpoints (Groq/Gemini via config):

  * POST /resume/draft     -> turn a student's VERIFIED profile into a clean,
                              recruiter-ready resume in Markdown. Uses ONLY the
                              verified skills/projects given, preserving the
                              "verified data moat" (no invented experience).
  * POST /resume/ats-score -> score a resume against a specific job description
                              (0-100) with matched / missing keywords and
                              concrete improvement suggestions.

Kept separate from the backend so heavy/latency-prone LLM work never blocks the
main API. Mounted under the `/resume` prefix by `main.py`.

Location:
    E:\\campus-ai\\ai-worker\\resume.py
"""

import json
from typing import Any

from fastapi import APIRouter, HTTPException, status
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from config import settings
from llm import get_chat_model
from tracing import trace_config

router = APIRouter(prefix="/resume", tags=["resume"])


# --- Schemas ---------------------------------------------------------------
class ResumeProject(BaseModel):
    title: str
    contribution: str | None = None
    description: str | None = None


class ResumeInternship(BaseModel):
    """A verified internship / OJT / training entry (real work experience)."""

    organization: str
    role_title: str
    internship_type: str | None = None
    mode: str | None = None
    location: str | None = None
    description: str | None = None
    skills_used: str | None = None
    duration: str | None = None


class ResumeProfile(BaseModel):
    """The student's VERIFIED data - the only ground truth for the resume."""

    full_name: str
    email: str | None = None
    phone: str | None = None
    target_role: str | None = None
    degree: str | None = None
    college: str | None = None
    cgpa: float | None = None
    attendance_percentage: float | None = None
    verified_skills: list[str] = Field(default_factory=list)
    projects: list[ResumeProject] = Field(default_factory=list)
    internships: list[ResumeInternship] = Field(default_factory=list)


class ResumeDraftRequest(BaseModel):
    profile: ResumeProfile


class ResumeDraftResponse(BaseModel):
    markdown: str
    provider: str


class AtsScoreRequest(BaseModel):
    resume_text: str = Field(min_length=1, max_length=20000)
    job_description: str = Field(min_length=1, max_length=20000)


class AtsScoreResponse(BaseModel):
    score: int = Field(ge=0, le=100)
    verdict: str
    matched_keywords: list[str]
    missing_keywords: list[str]
    suggestions: list[str]
    provider: str


# --- Helpers ---------------------------------------------------------------
def _extract_json(text: str) -> dict[str, Any]:
    """Best-effort parse of a JSON object from an LLM reply.

    Slices the outermost braces so it tolerates code fences (```json ... ```)
    or stray prose around the JSON.
    """
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("no JSON object found in model output")
    return json.loads(text[start : end + 1])


def _format_profile_for_draft(p: ResumeProfile) -> str:
    """Render the verified profile as compact text for the resume prompt."""
    lines = [f"Full name: {p.full_name}"]
    if p.email:
        lines.append(f"Email: {p.email}")
    if p.phone:
        lines.append(f"Phone: {p.phone}")
    if p.target_role:
        lines.append(f"Target role: {p.target_role}")
    if p.degree or p.college:
        edu = " — ".join(x for x in (p.degree, p.college) if x)
        lines.append(f"Education: {edu}")
    if p.cgpa is not None:
        lines.append(f"CGPA: {p.cgpa}")
    if p.attendance_percentage is not None:
        lines.append(f"Attendance: {p.attendance_percentage}%")
    skills = (
        ", ".join(p.verified_skills)
        if p.verified_skills
        else "(none verified yet)"
    )
    lines.append(f"Verified skills: {skills}")
    if p.internships:
        lines.append("Verified work experience (internships/OJT/training):")
        for it in p.internships:
            header_bits = [it.role_title, it.organization]
            header = " at ".join(x for x in header_bits if x)
            meta_bits = [
                it.internship_type,
                it.mode,
                it.location,
                it.duration,
            ]
            meta = ", ".join(x for x in meta_bits if x)
            line = f"  - {header}"
            if meta:
                line += f" ({meta})"
            lines.append(line)
            if it.description:
                lines.append(f"      {it.description}")
            if it.skills_used:
                lines.append(f"      Skills used: {it.skills_used}")
    else:
        lines.append("Verified work experience: (none verified yet)")
    if p.projects:
        lines.append("Verified projects:")
        for pr in p.projects:
            detail = pr.contribution or pr.description or "contributor"
            lines.append(f"  - {pr.title}: {detail}")
    else:
        lines.append("Verified projects: (none verified yet)")
    return "\n".join(lines)


_DRAFT_SYSTEM = (
    "You are an expert technical resume writer for college students applying "
    "to campus placements. Build a clean, ATS-friendly, single-page resume in "
    "GitHub-flavored Markdown using ONLY the verified facts provided. Do NOT "
    "invent experience, skills, dates, employers, or metrics that are not "
    "given. If a section has no data, omit it. Use strong action verbs and "
    "concise, impact-oriented bullet points. Structure: a header (name + any "
    "contact details), a 2-3 line Professional Summary tailored to the target "
    "role, Skills (grouped logically), Experience (each verified "
    "internship/OJT/training as a role at an organization, with its "
    "type/mode/location and duration, plus 1-2 impact bullets derived from the "
    "description/skills), Projects (bullets derived from each "
    "contribution/description), and Education. Place the Experience section "
    "before Projects when work experience exists. Return ONLY the Markdown "
    "resume with no extra commentary."
)

_ATS_SYSTEM = (
    "You are an ATS (Applicant Tracking System) engine and a technical "
    "recruiter. Compare the RESUME against the JOB DESCRIPTION and return a "
    "STRICT JSON object (no markdown, no prose) with EXACTLY these keys:\n"
    '  "score": integer 0-100 for overall match,\n'
    '  "verdict": one short sentence summarising the fit,\n'
    '  "matched_keywords": array of important JD skills/terms present in the resume,\n'
    '  "missing_keywords": array of important JD skills/terms absent from the resume,\n'
    '  "suggestions": array of 3-6 short, concrete tips to improve the match.\n'
    "Judge only on the text provided; do not assume facts that are not present."
)


# --- Endpoints -------------------------------------------------------------
@router.post("/draft", response_model=ResumeDraftResponse)
def draft_resume(payload: ResumeDraftRequest) -> ResumeDraftResponse:
    """Generate a Markdown resume from the student's verified profile."""
    messages = [
        SystemMessage(content=_DRAFT_SYSTEM),
        HumanMessage(content=_format_profile_for_draft(payload.profile)),
    ]
    try:
        result = get_chat_model().invoke(
            messages,
            config=trace_config("resume_draft", provider=settings.LLM_PROVIDER),
        )
    except Exception as exc:  # noqa: BLE001 - surface any provider/SDK error
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM call failed: {exc}",
        )
    return ResumeDraftResponse(
        markdown=str(result.content), provider=settings.LLM_PROVIDER
    )


@router.post("/ats-score", response_model=AtsScoreResponse)
def ats_score(payload: AtsScoreRequest) -> AtsScoreResponse:
    """Score a resume against a job description with matched/missing keywords."""
    user = (
        f"JOB DESCRIPTION:\n{payload.job_description}\n\n"
        f"RESUME:\n{payload.resume_text}"
    )
    messages = [
        SystemMessage(content=_ATS_SYSTEM),
        HumanMessage(content=user),
    ]
    try:
        result = get_chat_model().invoke(
            messages,
            config=trace_config("resume_ats_score", provider=settings.LLM_PROVIDER),
        )
    except Exception as exc:  # noqa: BLE001 - surface any provider/SDK error
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM call failed: {exc}",
        )
    try:
        data = _extract_json(str(result.content))
    except Exception as exc:  # noqa: BLE001 - malformed model output
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not parse ATS result from the model: {exc}",
        )

    # Defensively normalise the model's output.
    try:
        score = max(0, min(100, int(round(float(data.get("score", 0))))))
    except (TypeError, ValueError):
        score = 0

    def _str_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item) for item in value]

    return AtsScoreResponse(
        score=score,
        verdict=str(data.get("verdict", "")),
        matched_keywords=_str_list(data.get("matched_keywords")),
        missing_keywords=_str_list(data.get("missing_keywords")),
        suggestions=_str_list(data.get("suggestions")),
        provider=settings.LLM_PROVIDER,
    )
