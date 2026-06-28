"""AI Resume builder + ATS scoring + version history (student-facing backend).

Gathers the student's VERIFIED profile and asks the AI worker to:
  * draft a recruiter-ready Markdown resume  -> POST /resume/generate
  * score any resume against a job description -> POST /resume/ats-score

Version history (the moat, persisted):
  * every generate saves an immutable snapshot in the `resumes` table
  * the student can list / open / rename / delete versions and mark ONE primary
    -> GET /resume/versions, GET/PATCH/DELETE /resume/versions/{id}

Verified-only by design: the resume is built from the same moat data the mentor
uses, so unproven claims never reach a recruiter-facing document.

Mounted under the `/resume` prefix by `main.py`.

Location:
    E:\\campus-ai\\backend\\resume.py
"""

from datetime import datetime

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
    Resume,
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
    # Optional custom label for the saved version (else auto-generated).
    title: str | None = Field(default=None, max_length=150)
    # Persist this generation as a new version (default on).
    save: bool = True


class ResumeGenerateResponse(BaseModel):
    markdown: str
    provider: str
    # The id of the saved version (None when save=False).
    version_id: int | None = None


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


class ResumeVersionSummary(BaseModel):
    """Lightweight list item (no full markdown, just a short preview)."""

    id: int
    title: str
    target_role: str | None
    provider: str | None
    is_primary: bool
    created_at: datetime
    preview: str


class ResumeVersionOut(BaseModel):
    """Full version detail (includes the saved markdown)."""

    id: int
    title: str
    target_role: str | None
    provider: str | None
    is_primary: bool
    created_at: datetime
    markdown: str


class ResumeVersionUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=150)
    is_primary: bool | None = None


# --- Helpers ---------------------------------------------------------------
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


def _default_title(target_role: str | None) -> str:
    """Build a friendly auto-title like 'Backend Engineer resume - 28 Jun 2026'."""
    stamp = datetime.now().strftime("%d %b %Y")
    role = (target_role or "").strip()
    return f"{role} resume - {stamp}" if role else f"Resume - {stamp}"


def _preview(markdown: str, length: int = 160) -> str:
    """Collapse whitespace and trim to a short one-line preview."""
    text = " ".join(markdown.split())
    return text[:length] + ("..." if len(text) > length else "")


def _summary(version: Resume) -> ResumeVersionSummary:
    return ResumeVersionSummary(
        id=version.id,
        title=version.title,
        target_role=version.target_role,
        provider=version.provider,
        is_primary=version.is_primary,
        created_at=version.created_at,
        preview=_preview(version.markdown),
    )


def _detail(version: Resume) -> ResumeVersionOut:
    return ResumeVersionOut(
        id=version.id,
        title=version.title,
        target_role=version.target_role,
        provider=version.provider,
        is_primary=version.is_primary,
        created_at=version.created_at,
        markdown=version.markdown,
    )


def _own_version_or_404(
    db: Session, student: User, version_id: int
) -> Resume:
    """Fetch a version that belongs to this student, else 404."""
    version = db.get(Resume, version_id)
    if version is None or version.student_id != student.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume version not found.",
        )
    return version


# --- Routes ----------------------------------------------------------------
@router.post("/generate", response_model=ResumeGenerateResponse)
def generate(
    payload: ResumeGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResumeGenerateResponse:
    """Build a Markdown resume from YOUR verified profile (and save a version)."""
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

    markdown = result["markdown"]
    provider = result.get("provider", "unknown")

    version_id: int | None = None
    if payload.save:
        version = Resume(
            student_id=current_user.id,
            title=(payload.title or "").strip() or _default_title(payload.target_role),
            target_role=(payload.target_role or None),
            markdown=markdown,
            provider=provider,
        )
        db.add(version)
        db.commit()
        db.refresh(version)
        version_id = version.id

    return ResumeGenerateResponse(
        markdown=markdown, provider=provider, version_id=version_id
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


@router.get("/versions", response_model=list[ResumeVersionSummary])
def list_versions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ResumeVersionSummary]:
    """List YOUR saved resume versions, newest first."""
    rows = list(
        db.scalars(
            select(Resume)
            .where(Resume.student_id == current_user.id)
            .order_by(Resume.created_at.desc())
        )
    )
    return [_summary(v) for v in rows]


@router.get("/versions/{version_id}", response_model=ResumeVersionOut)
def get_version(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResumeVersionOut:
    """Open one of YOUR saved resume versions (full markdown)."""
    version = _own_version_or_404(db, current_user, version_id)
    return _detail(version)


@router.patch("/versions/{version_id}", response_model=ResumeVersionOut)
def update_version(
    version_id: int,
    payload: ResumeVersionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResumeVersionOut:
    """Rename a version and/or set it as your primary resume."""
    version = _own_version_or_404(db, current_user, version_id)

    if payload.title is not None:
        new_title = payload.title.strip()
        if not new_title:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Title cannot be empty.",
            )
        version.title = new_title

    if payload.is_primary is not None:
        if payload.is_primary:
            # Demote any other primary version first (at most one per student).
            others = db.scalars(
                select(Resume).where(
                    Resume.student_id == current_user.id,
                    Resume.is_primary.is_(True),
                    Resume.id != version.id,
                )
            ).all()
            for other in others:
                other.is_primary = False
            version.is_primary = True
        else:
            version.is_primary = False

    db.commit()
    db.refresh(version)
    return _detail(version)


@router.delete("/versions/{version_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_version(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete one of YOUR saved resume versions."""
    version = _own_version_or_404(db, current_user, version_id)
    db.delete(version)
    db.commit()
