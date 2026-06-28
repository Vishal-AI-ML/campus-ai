"""Extra-curricular activities (ECA) routes - the 'well-rounded student' moat.

Same verified-data lifecycle as skills (sports, cultural, leadership, ...):
  * STUDENT logs an activity with proof -> starts `pending`; can view/delete own.
  * TEACHER or TPO reviews the queue and verifies/flags each claim.
  * Only `verified` activities count toward the profile / recruiter view.

Unlike skills there is no AI proof-scoring step (a teacher/TPO simply confirms
the certificate/evidence). Mounted under the `/eca` prefix by `main.py`.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db import get_db
from models import ExtraCurricular, SkillStatus, User, UserRole
from schemas import ECACreate, ECADecision, ECAOut
from security import get_current_user, require_roles

router = APIRouter(prefix="/eca", tags=["eca"])

# Either a teacher (mentor) or the TPO may verify ECA claims and read a
# student's activities (e.g. for eligibility / placement context).
reviewer_only = require_roles(UserRole.teacher, UserRole.tpo)
staff_only = require_roles(UserRole.teacher, UserRole.tpo)


# --- Student: log & view own activities ------------------------------------
@router.post("", response_model=ECAOut, status_code=status.HTTP_201_CREATED)
def claim_eca(
    payload: ECACreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExtraCurricular:
    """Log an extra-curricular activity for yourself (starts `pending`).
    Activity title must be unique per student."""
    eca = ExtraCurricular(
        student_id=current_user.id,
        title=payload.title,
        category=payload.category,
        organization=payload.organization,
        description=payload.description,
        evidence_url=payload.evidence_url,
        status=SkillStatus.pending,
    )
    db.add(eca)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already logged an activity with this title",
        )
    db.refresh(eca)
    return eca


@router.get("/me", response_model=list[ECAOut])
def my_eca(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ExtraCurricular]:
    """List the logged-in user's own ECA claims (any status)."""
    return list(
        db.scalars(
            select(ExtraCurricular)
            .where(ExtraCurricular.student_id == current_user.id)
            .order_by(ExtraCurricular.created_at.desc())
        )
    )


@router.delete("/{eca_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_eca(
    eca_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete one of your own ECA claims."""
    eca = db.get(ExtraCurricular, eca_id)
    if eca is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found"
        )
    if eca.student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own activities",
        )
    db.delete(eca)
    db.commit()


# --- Reviewer (teacher/TPO): verification queue & decisions ----------------
@router.get(
    "/queue", response_model=list[ECAOut], dependencies=[Depends(reviewer_only)]
)
def verification_queue(
    status_filter: SkillStatus = SkillStatus.pending,
    db: Session = Depends(get_db),
) -> list[ExtraCurricular]:
    """The reviewer's queue. Defaults to pending claims (oldest first)."""
    return list(
        db.scalars(
            select(ExtraCurricular)
            .where(ExtraCurricular.status == status_filter)
            .order_by(ExtraCurricular.created_at.asc())
        )
    )


@router.patch("/{eca_id}/decision", response_model=ECAOut)
def decide_eca(
    eca_id: int,
    payload: ECADecision,
    db: Session = Depends(get_db),
    reviewer: User = Depends(reviewer_only),
) -> ExtraCurricular:
    """Teacher/TPO verifies or flags an ECA claim. `pending` is not a target."""
    if payload.status not in (SkillStatus.verified, SkillStatus.flagged):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decision must be 'verified' or 'flagged'",
        )
    eca = db.get(ExtraCurricular, eca_id)
    if eca is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found"
        )
    eca.status = payload.status
    eca.review_note = payload.review_note
    eca.reviewed_by_id = reviewer.id
    eca.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(eca)
    return eca


# --- Staff: read a student's activities -------------------------------------
@router.get(
    "/student/{student_id}",
    response_model=list[ECAOut],
    dependencies=[Depends(staff_only)],
)
def student_eca(
    student_id: int,
    status_filter: SkillStatus | None = None,
    db: Session = Depends(get_db),
) -> list[ExtraCurricular]:
    """List a student's activities (teacher/TPO). Filter by status, e.g. verified."""
    stmt = select(ExtraCurricular).where(ExtraCurricular.student_id == student_id)
    if status_filter is not None:
        stmt = stmt.where(ExtraCurricular.status == status_filter)
    return list(db.scalars(stmt.order_by(ExtraCurricular.created_at.desc())))
