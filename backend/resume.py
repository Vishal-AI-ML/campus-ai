"""AI Resume builder + ATS scoring (student-facing backend).

Gathers the student's VERIFIED profile and asks the AI worker to:
  * draft a recruiter-ready Markdown resume  -> POST /resume/generate
  * score any resume against a job description -> POST /resume/ats-score

Verified-only by design: the resume is built from the same moat data the mentor
uses, so unproven claims never reach a recruiter-facing document. Generation is
on-the-fly (no stored versions yet); a `resumes` table can be added later for
version history.

Mounted under the `/resume` prefix by `main.py`.

Location:
    E:\\campus-ai\\backend\\resume.py
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai_client import generate_resume, score_resume_ats
from db import get_db
from models import (
    AttendanceRecord,
    AttendanceStatus,
    Project,
    ProjectMember,
    Result,
    Skill,
    SkillStatus,
    Subject,
    User,
)
from security import get_current_user

router = APIRouter(prefix="/resume", tags=["resume"])


# --- Schemas ---------------------------------------------------------------
class ResumeGenerateRequest(BaseModel):
    target_role: str | None = Field(
        default=None, max_length=120, examples=["Backend Engineer"]
    )


class ResumeGenerateResponse(BaseModel):
    markdown: str
    provider: str


class AtsScoreRequest(BaseModel):
    resume_text: str = Field(min_length=1, max_length=20000)
    job_description: str = Field(min_length=1, max_length=20000)


class AtsScoreResponse(BaseModel):
    score: int
    verdict: str
    matched_keywords: list[str]
    missing_keywords: list[str]
    suggestions: list[str]
    provider: str


def _build_resume_profile(
    db: Session, student: User, target_role: str | None
) -> dict:
    """Collect ONLY the student's verified data for the resume builder.

    Mirrors the mentor's profile gathering (same moat), plus identity fields
    (name, email) and the requested target role for tailoring.
    """
    # Verified skills (names only).
    skills = list(
        db.scalars(
            select(Skill.name).where(
                Skill.student_id == student.id,
                Skill.status == SkillStatus.verified,
            )
        )
    )

    # Verified project contributions (title + what they did).
    proj_rows = db.execute(
        select(Project.title, ProjectMember.contribution)
        .join(Project, ProjectMember.project_id == Project.id)
        .where(
            ProjectMember.student_id == student.id,
            ProjectMember.status == SkillStatus.verified,
        )
    ).all()
    projects = [
        {"title": title, "contribution": contribution}
        for title, contribution in proj_rows
    ]

    # Overall attendance % ((present + late) / total).
    statuses = list(
        db.scalars(
            select(AttendanceRecord.status).where(
                AttendanceRecord.student_id == student.id
            )
        )
    )
    total = len(statuses)
    attended = sum(
        1 for s in statuses if s in (AttendanceStatus.present, AttendanceStatus.late)
    )
    attendance_percentage = round(attended / total * 100, 1) if total else None

    # Credit-weighted CGPA across all results.
    gp_rows = db.execute(
        select(Result.grade_point, Subject.credits)
        .join(Subject, Result.subject_id == Subject.id)
        .where(Result.student_id == student.id)
    ).all()
    total_credits = sum(credits for _, credits in gp_rows)
    cgpa = (
        round(sum(gp * credits for gp, credits in gp_rows) / total_credits, 2)
        if total_credits
        else None
    )

    return {
        "full_name": student.full_name,
        "email": student.email,
        "target_role": target_role,
        "cgpa": cgpa,
        "attendance_percentage": attendance_percentage,
        "verified_skills": skills,
        "projects": projects,
    }


@router.post("/generate", response_model=ResumeGenerateResponse)
def generate(
    payload: ResumeGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResumeGenerateResponse:
    """Build a Markdown resume from YOUR verified profile."""
    profile = _build_resume_profile(db, current_user, payload.target_role)
    if not profile["verified_skills"] and not profile["projects"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "No verified skills or projects yet. Get some verified by your "
                "mentor before generating a resume."
            ),
        )
    result = generate_resume(profile)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Resume builder is unavailable right now (is the AI worker running?).",
        )
    return ResumeGenerateResponse(
        markdown=result["markdown"], provider=result.get("provider", "unknown")
    )


@router.post("/ats-score", response_model=AtsScoreResponse)
def ats_score(
    payload: AtsScoreRequest,
    current_user: User = Depends(get_current_user),
) -> AtsScoreResponse:
    """Score a resume against a job description (matched/missing keywords + tips)."""
    result = score_resume_ats(payload.resume_text, payload.job_description)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="ATS scorer is unavailable right now (is the AI worker running?).",
        )
    return AtsScoreResponse(
        score=int(result.get("score", 0)),
        verdict=str(result.get("verdict", "")),
        matched_keywords=list(result.get("matched_keywords", []) or []),
        missing_keywords=list(result.get("missing_keywords", []) or []),
        suggestions=list(result.get("suggestions", []) or []),
        provider=result.get("provider", "unknown"),
    )
