"""Skills routes - the 'verified data moat'.

Role model (matches the prototype's 'Verification queue: AI assists, mentor
decides'):
  * STUDENT (any logged-in user) claims a skill with proof -> it starts as
    `pending`, and they can view/delete their own claims.
  * MENTOR (teacher role) sees the pending queue and verifies or flags each
    claim. Only `verified` skills should count toward resume/eligibility.
  * TEACHER/TPO can read a given student's skills (e.g. for eligibility).

On claim, a BackgroundTask asks the AI worker to score the proof and fill
`ai_score` (advisory; the mentor still decides).

Mounted under the `/skills` prefix by `main.py`.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ai_client import score_skill
from db import get_db
from models import Skill, SkillStatus, User, UserRole
from schemas import SkillCreate, SkillDecision, SkillOut
from security import get_current_tenant_id, get_current_user, require_roles

router = APIRouter(prefix="/skills", tags=["skills"])

# Mentors are teachers; some reads are open to TPO too.
mentor_only = require_roles(UserRole.teacher)
staff_only = require_roles(UserRole.teacher, UserRole.tpo)


# --- Student: claim & view own skills --------------------------------------
@router.post("", response_model=SkillOut, status_code=status.HTTP_201_CREATED)
def claim_skill(
    payload: SkillCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Skill:
    """Claim a skill for yourself (starts `pending`). Skill name must be unique
    per student. The AI worker scores the proof in the background."""
    skill = Skill(
        student_id=current_user.id,
        tenant_id=current_user.tenant_id,
        name=payload.name,
        evidence_url=payload.evidence_url,
        evidence_note=payload.evidence_note,
        status=SkillStatus.pending,
    )
    db.add(skill)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already claimed this skill",
        )
    db.refresh(skill)
    # Fire-and-forget AI proof scoring (fills ai_score); never blocks the user.
    background_tasks.add_task(score_skill, skill.id)
    return skill


@router.get("/me", response_model=list[SkillOut])
def my_skills(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Skill]:
    """List the logged-in user's own skill claims (any status)."""
    return list(
        db.scalars(
            select(Skill)
            .where(
                Skill.student_id == current_user.id,
                Skill.tenant_id == current_user.tenant_id,
            )
            .order_by(Skill.created_at.desc())
        )
    )


@router.delete("/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_skill(
    skill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete one of your own skill claims."""
    skill = db.get(Skill, skill_id)
    if skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found"
        )
    if skill.student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own skills",
        )
    db.delete(skill)
    db.commit()


# --- Mentor: verification queue & decisions --------------------------------
@router.get(
    "/queue", response_model=list[SkillOut], dependencies=[Depends(mentor_only)]
)
def verification_queue(
    status_filter: SkillStatus = SkillStatus.pending,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
) -> list[Skill]:
    """The mentor's review queue. Defaults to pending claims (oldest first).

    Tenant-scoped: a mentor only ever sees claims from their own institute.
    """
    return list(
        db.scalars(
            select(Skill)
            .where(Skill.tenant_id == tenant_id, Skill.status == status_filter)
            .order_by(Skill.created_at.asc())
        )
    )


@router.patch("/{skill_id}/decision", response_model=SkillOut)
def decide_skill(
    skill_id: int,
    payload: SkillDecision,
    db: Session = Depends(get_db),
    mentor: User = Depends(mentor_only),
) -> Skill:
    """Mentor verifies or flags a skill claim. `pending` is not a valid target."""
    if payload.status not in (SkillStatus.verified, SkillStatus.flagged):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decision must be 'verified' or 'flagged'",
        )
    skill = db.get(Skill, skill_id)
    # Tenant guard: a mentor can only act on claims from their own institute.
    # Treating a cross-tenant row as 404 also avoids leaking that the id exists.
    if skill is None or skill.tenant_id != mentor.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found"
        )
    skill.status = payload.status
    skill.review_note = payload.review_note
    skill.reviewed_by_id = mentor.id
    skill.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(skill)
    return skill


# --- Staff: read a student's skills (e.g. for eligibility) -----------------
@router.get(
    "/student/{student_id}",
    response_model=list[SkillOut],
    dependencies=[Depends(staff_only)],
)
def student_skills(
    student_id: int,
    status_filter: SkillStatus | None = None,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
) -> list[Skill]:
    """List a student's skills (teacher/TPO). Filter by status, e.g. verified.

    Tenant-scoped: staff can only read students within their own institute.
    """
    stmt = select(Skill).where(
        Skill.student_id == student_id, Skill.tenant_id == tenant_id
    )
    if status_filter is not None:
        stmt = stmt.where(Skill.status == status_filter)
    return list(db.scalars(stmt.order_by(Skill.created_at.desc())))
