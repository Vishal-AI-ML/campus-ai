"""Doubt Forum module.

A section-scoped Q&A board (the student-facing "Doubts" feature):
  * ASK     - a student posts a doubt in their OWN section (staff may post to
              any section), optionally tied to a subject.
  * ANSWER  - any member of that section (or staff) answers the doubt.
  * UPVOTE  - any logged-in user toggles a single upvote per answer.
  * ACCEPT  - the asker (or staff) accepts one answer -> the doubt is resolved.

Students are scoped to their own section throughout; teachers/admins/tpo are
treated as staff and may access any section's forum. Mounted under the
`/doubts` prefix by `main.py`.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from db import get_db
from models import (
    AnswerVote,
    Doubt,
    DoubtAnswer,
    DoubtStatus,
    Section,
    Subject,
    User,
    UserRole,
)
from schemas import (
    AnswerCreate,
    AnswerOut,
    DoubtCreate,
    DoubtDetailOut,
    DoubtOut,
)
from security import (
    get_current_tenant_id,
    get_current_user,
    require_roles,
)

router = APIRouter(prefix="/doubts", tags=["doubts"])

# Listing every section's doubts (governance view) is staff-only.
staff_only = require_roles(UserRole.teacher, UserRole.admin)

# Roles treated as "staff" for section-access checks (can reach any section).
STAFF_ROLES = (UserRole.teacher, UserRole.admin, UserRole.tpo)


def _is_staff(user: User) -> bool:
    return user.role in STAFF_ROLES


def _ensure_section_access(user: User, section_id: int) -> None:
    """Students may only touch their own section's forum; staff reach any."""
    if not _is_staff(user) and user.section_id != section_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access this section's forum",
        )


def _answer_out(db: Session, answer: DoubtAnswer, viewer: User) -> AnswerOut:
    """Build an AnswerOut with a live upvote count + the viewer's vote state."""
    upvotes = db.scalar(
        select(func.count())
        .select_from(AnswerVote)
        .where(AnswerVote.answer_id == answer.id)
    )
    viewer_vote = db.scalar(
        select(func.count())
        .select_from(AnswerVote)
        .where(
            AnswerVote.answer_id == answer.id,
            AnswerVote.user_id == viewer.id,
        )
    )
    return AnswerOut(
        id=answer.id,
        doubt_id=answer.doubt_id,
        body=answer.body,
        answered_by_id=answer.answered_by_id,
        is_accepted=answer.is_accepted,
        upvote_count=int(upvotes or 0),
        viewer_has_upvoted=bool(viewer_vote),
        created_at=answer.created_at,
    )


def _doubt_out(db: Session, doubt: Doubt) -> DoubtOut:
    """Build a DoubtOut list item with a live answer count."""
    answer_count = db.scalar(
        select(func.count())
        .select_from(DoubtAnswer)
        .where(DoubtAnswer.doubt_id == doubt.id)
    )
    return DoubtOut(
        id=doubt.id,
        section_id=doubt.section_id,
        subject_id=doubt.subject_id,
        title=doubt.title,
        body=doubt.body,
        status=doubt.status,
        asked_by_id=doubt.asked_by_id,
        answer_count=int(answer_count or 0),
        created_at=doubt.created_at,
        resolved_at=doubt.resolved_at,
    )


def _doubt_detail(db: Session, doubt: Doubt, viewer: User) -> DoubtDetailOut:
    """A doubt + its answers, sorted accepted-first then by most upvotes."""
    answers = db.scalars(
        select(DoubtAnswer).where(DoubtAnswer.doubt_id == doubt.id)
    )
    answer_outs = [_answer_out(db, a, viewer) for a in answers]
    answer_outs.sort(
        key=lambda a: (not a.is_accepted, -a.upvote_count, a.created_at)
    )
    base = _doubt_out(db, doubt)
    return DoubtDetailOut(**base.model_dump(), answers=answer_outs)


@router.post("", response_model=DoubtOut, status_code=status.HTTP_201_CREATED)
def create_doubt(
    payload: DoubtCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DoubtOut:
    """Post a new doubt. Students may only post in their own section."""
    if db.get(Section, payload.section_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Section not found"
        )
    _ensure_section_access(current_user, payload.section_id)
    if (
        payload.subject_id is not None
        and db.get(Subject, payload.subject_id) is None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found"
        )
    doubt = Doubt(
        tenant_id=current_user.tenant_id,
        section_id=payload.section_id,
        subject_id=payload.subject_id,
        title=payload.title,
        body=payload.body,
        asked_by_id=current_user.id,
    )
    db.add(doubt)
    db.commit()
    db.refresh(doubt)
    return _doubt_out(db, doubt)


@router.get(
    "",
    response_model=list[DoubtOut],
    dependencies=[Depends(staff_only)],
)
def list_doubts(
    section_id: int | None = None,
    subject_id: int | None = None,
    status_filter: DoubtStatus | None = None,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
) -> list[DoubtOut]:
    """List doubts (staff), optionally filtered by section/subject/status.

    Tenant-scoped: staff only ever see their own institute's doubts.
    """
    stmt = select(Doubt).where(Doubt.tenant_id == tenant_id)
    if section_id is not None:
        stmt = stmt.where(Doubt.section_id == section_id)
    if subject_id is not None:
        stmt = stmt.where(Doubt.subject_id == subject_id)
    if status_filter is not None:
        stmt = stmt.where(Doubt.status == status_filter)
    doubts = db.scalars(stmt.order_by(Doubt.created_at.desc()))
    return [_doubt_out(db, d) for d in doubts]


@router.get("/me", response_model=list[DoubtOut])
def my_doubts(
    subject_id: int | None = None,
    status_filter: DoubtStatus | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DoubtOut]:
    """The forum feed for the logged-in user's own section."""
    if current_user.section_id is None:
        return []
    stmt = select(Doubt).where(Doubt.section_id == current_user.section_id)
    if subject_id is not None:
        stmt = stmt.where(Doubt.subject_id == subject_id)
    if status_filter is not None:
        stmt = stmt.where(Doubt.status == status_filter)
    doubts = db.scalars(stmt.order_by(Doubt.created_at.desc()))
    return [_doubt_out(db, d) for d in doubts]


@router.get("/{doubt_id}", response_model=DoubtDetailOut)
def get_doubt(
    doubt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DoubtDetailOut:
    """Open a doubt + its answers. Students only within their own section."""
    doubt = db.get(Doubt, doubt_id)
    # Tenant guard: a doubt from another institute is hidden as 404.
    if doubt is None or doubt.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Doubt not found"
        )
    _ensure_section_access(current_user, doubt.section_id)
    return _doubt_detail(db, doubt, current_user)


@router.post(
    "/{doubt_id}/answers",
    response_model=AnswerOut,
    status_code=status.HTTP_201_CREATED,
)
def create_answer(
    doubt_id: int,
    payload: AnswerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnswerOut:
    """Answer a doubt (any member of its section, or staff)."""
    doubt = db.get(Doubt, doubt_id)
    # Tenant guard: a doubt from another institute is hidden as 404.
    if doubt is None or doubt.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Doubt not found"
        )
    _ensure_section_access(current_user, doubt.section_id)
    answer = DoubtAnswer(
        tenant_id=current_user.tenant_id,
        doubt_id=doubt.id,
        body=payload.body,
        answered_by_id=current_user.id,
    )
    db.add(answer)
    db.commit()
    db.refresh(answer)
    return _answer_out(db, answer, current_user)


@router.post(
    "/{doubt_id}/answers/{answer_id}/accept",
    response_model=DoubtDetailOut,
)
def accept_answer(
    doubt_id: int,
    answer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DoubtDetailOut:
    """Accept an answer as the solution (asker or staff). Resolves the doubt."""
    doubt = db.get(Doubt, doubt_id)
    # Tenant guard: a doubt from another institute is hidden as 404.
    if doubt is None or doubt.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Doubt not found"
        )
    answer = db.get(DoubtAnswer, answer_id)
    if answer is None or answer.doubt_id != doubt.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Answer not found"
        )
    if not _is_staff(current_user) and doubt.asked_by_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the asker or staff can accept an answer",
        )
    # Exactly one accepted answer: clear the rest, mark this one.
    for a in doubt.answers:
        a.is_accepted = a.id == answer.id
    doubt.status = DoubtStatus.resolved
    doubt.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(doubt)
    return _doubt_detail(db, doubt, current_user)


@router.post("/answers/{answer_id}/upvote", response_model=AnswerOut)
def toggle_upvote(
    answer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnswerOut:
    """Toggle a single upvote on an answer (one per user)."""
    answer = db.get(DoubtAnswer, answer_id)
    # Tenant guard: an answer from another institute is hidden as 404.
    if answer is None or answer.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Answer not found"
        )
    doubt = db.get(Doubt, answer.doubt_id)
    if doubt is not None:
        _ensure_section_access(current_user, doubt.section_id)
    existing = db.scalar(
        select(AnswerVote).where(
            AnswerVote.answer_id == answer_id,
            AnswerVote.user_id == current_user.id,
        )
    )
    if existing is None:
        db.add(
            AnswerVote(
                tenant_id=current_user.tenant_id,
                answer_id=answer_id,
                user_id=current_user.id,
            )
        )
    else:
        db.delete(existing)
    db.commit()
    return _answer_out(db, answer, current_user)


@router.delete("/{doubt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_doubt(
    doubt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a doubt. Admins can delete any; otherwise only your own."""
    doubt = db.get(Doubt, doubt_id)
    # Tenant guard: a doubt from another institute is hidden as 404.
    if doubt is None or doubt.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Doubt not found"
        )
    if (
        current_user.role != UserRole.admin
        and doubt.asked_by_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own doubt",
        )
    db.delete(doubt)
    db.commit()
