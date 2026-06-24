"""AI Career Mentor endpoint (student-facing).

Gathers the student's VERIFIED profile from the database and asks the AI worker
for grounded career guidance. Verified-only by design - this is the moat:
unverified claims never reach the mentor's context, so advice can't be built on
unproven data.

Mounted under the `/mentor` prefix by `main.py`.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai_client import ask_mentor
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

router = APIRouter(prefix="/mentor", tags=["mentor"])


class ChatTurn(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class MentorChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000, examples=["Backend role ke liye mera skill gap kya hai?"])
    history: list[ChatTurn] = Field(default_factory=list)


class MentorChatResponse(BaseModel):
    answer: str
    provider: str


def _build_verified_profile(db: Session, student_id: int) -> dict:
    """Collect ONLY the student's verified data for the mentor's context."""
    # Verified skills (names only).
    skills = list(
        db.scalars(
            select(Skill.name).where(
                Skill.student_id == student_id, Skill.status == SkillStatus.verified
            )
        )
    )

    # Verified project contributions (title + what they did).
    proj_rows = db.execute(
        select(Project.title, ProjectMember.contribution)
        .join(Project, ProjectMember.project_id == Project.id)
        .where(
            ProjectMember.student_id == student_id,
            ProjectMember.status == SkillStatus.verified,
        )
    ).all()
    projects = [{"title": title, "contribution": contribution} for title, contribution in proj_rows]

    # Overall attendance % ((present + late) / total).
    statuses = list(
        db.scalars(
            select(AttendanceRecord.status).where(
                AttendanceRecord.student_id == student_id
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
        select(Result.grade_point, Subject.credits).join(
            Subject, Result.subject_id == Subject.id
        ).where(Result.student_id == student_id)
    ).all()
    total_credits = sum(credits for _, credits in gp_rows)
    cgpa = (
        round(sum(gp * credits for gp, credits in gp_rows) / total_credits, 2)
        if total_credits
        else None
    )

    return {
        "verified_skills": skills,
        "projects": projects,
        "attendance_percentage": attendance_percentage,
        "cgpa": cgpa,
    }


@router.post("/chat", response_model=MentorChatResponse)
def mentor_chat(
    payload: MentorChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MentorChatResponse:
    """Ask the AI mentor a question, grounded on YOUR verified profile."""
    profile = _build_verified_profile(db, current_user.id)
    result = ask_mentor(
        profile, payload.question, [turn.model_dump() for turn in payload.history]
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI mentor is unavailable right now (is the AI worker running?)",
        )
    return MentorChatResponse(
        answer=result["answer"], provider=result.get("provider", "unknown")
    )
