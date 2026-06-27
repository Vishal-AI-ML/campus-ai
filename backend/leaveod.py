"""Leave & On-Duty (OD) module.

Two kinds of planned absence, deliberately kept distinct because they affect
attendance differently:

  * LEAVE - a personal absence (medical / personal / emergency). The student
    applies; a class teacher / mentor / admin approves or rejects.
  * OD ("on duty") - the student is away on OFFICIAL college work (fest,
    hackathon, sports, paper presentation, NSS/NCC, industrial visit,
    placement interview, ...). Approved OD is *condoned*: it must not pull the
    student's attendance percentage down.

Workflow
  * apply for your OWN request                     -> POST  /leave
  * STAFF raise bulk OD for many students (event)  -> POST  /leave/bulk-od
  * view your own requests                         -> GET   /leave/me
  * STAFF list/filter requests (approval inbox)    -> GET   /leave
  * open one request                               -> GET   /leave/{id}
  * STAFF approve / reject a pending request       -> PATCH /leave/{id}/decision
  * applicant cancels (withdraws) a request        -> POST  /leave/{id}/cancel
  * applicant (own) or admin deletes a request     -> DELETE /leave/{id}

Attendance condonation is wired in `attendance.py`: an approved leave/OD
excuses any matching `absent` records (removed from the percentage
denominator) so official duty / approved leave never lowers the student's
attendance %.
Mounted under the `/leave` prefix by `main.py`.
"""

import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from db import get_db
from models import (
    LeaveRequest,
    LeaveRequestType,
    LeaveStatus,
    Section,
    User,
    UserRole,
)
from schemas import (
    BulkODCreate,
    BulkODResult,
    LeaveDecision,
    LeaveRequestCreate,
    LeaveRequestOut,
)
from security import get_current_user, require_roles

router = APIRouter(prefix="/leave", tags=["leave-od"])

# Approving, raising bulk OD and listing every request is staff work.
staff_only = require_roles(UserRole.teacher, UserRole.admin)

# Roles that may reach any section / see every request.
STAFF_ROLES = (UserRole.teacher, UserRole.admin, UserRole.tpo)

# Allowed sub-categories per request type. Kept here (not in the DB) so adding a
# new event type is a one-line change with no migration.
LEAVE_CATEGORIES = {"medical", "personal", "emergency"}
OD_CATEGORIES = {
    "fest",
    "technical",
    "sports",
    "competition",
    "ncc_nss",
    "industrial_visit",
    "placement",
    "other",
}


def _is_staff(user: User) -> bool:
    return user.role in STAFF_ROLES


def _validate_dates(start: date, end: date) -> None:
    """A request must end on or after it starts."""
    if end < start:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_date must be on or after start_date",
        )


def _validate_category(request_type: LeaveRequestType, category: str) -> str:
    """Normalise + validate the category against the chosen request type."""
    allowed = (
        OD_CATEGORIES if request_type == LeaveRequestType.od else LEAVE_CATEGORIES
    )
    value = category.strip().lower()
    if value not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Invalid category '{category}' for {request_type.value}. "
                f"Allowed: {sorted(allowed)}"
            ),
        )
    return value


def _out(db: Session, req: LeaveRequest) -> LeaveRequestOut:
    """Build a LeaveRequestOut enriched with display names + a day count."""
    student = db.get(User, req.student_id)
    section = db.get(Section, req.section_id) if req.section_id else None
    reviewer = db.get(User, req.reviewed_by_id) if req.reviewed_by_id else None
    return LeaveRequestOut(
        id=req.id,
        request_type=req.request_type,
        category=req.category,
        student_id=req.student_id,
        student_name=student.full_name if student else None,
        section_id=req.section_id,
        section_name=section.name if section else None,
        title=req.title,
        reason=req.reason,
        event_name=req.event_name,
        proof_url=req.proof_url,
        start_date=req.start_date,
        end_date=req.end_date,
        status=req.status,
        applied_by_id=req.applied_by_id,
        reviewed_by_id=req.reviewed_by_id,
        reviewer_name=reviewer.full_name if reviewer else None,
        review_note=req.review_note,
        reviewed_at=req.reviewed_at,
        bulk_group_id=req.bulk_group_id,
        days=(req.end_date - req.start_date).days + 1,
        created_at=req.created_at,
    )


@router.post("", response_model=LeaveRequestOut, status_code=status.HTTP_201_CREATED)
def apply_leave(
    payload: LeaveRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LeaveRequestOut:
    """Apply for your OWN leave or OD. Starts `pending` for staff review."""
    _validate_dates(payload.start_date, payload.end_date)
    category = _validate_category(payload.request_type, payload.category)
    req = LeaveRequest(
        request_type=payload.request_type,
        category=category,
        student_id=current_user.id,
        section_id=current_user.section_id,
        title=payload.title,
        reason=payload.reason,
        event_name=payload.event_name,
        proof_url=payload.proof_url,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status=LeaveStatus.pending,
        applied_by_id=current_user.id,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return _out(db, req)


@router.post(
    "/bulk-od",
    response_model=BulkODResult,
    status_code=status.HTTP_201_CREATED,
)
def create_bulk_od(
    payload: BulkODCreate,
    db: Session = Depends(get_db),
    staff: User = Depends(staff_only),
) -> BulkODResult:
    """Raise ON-DUTY for many students at once (fest / sports / group event).

    Each student gets their own auto-approved OD row, all linked by one
    `bulk_group_id`. Unknown ids or non-student accounts are skipped and
    reported back in `skipped`.
    """
    _validate_dates(payload.start_date, payload.end_date)
    category = _validate_category(LeaveRequestType.od, payload.category)
    bulk_group_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    created: list[LeaveRequest] = []
    skipped: list[int] = []
    seen: set[int] = set()
    for sid in payload.student_ids:
        if sid in seen:
            continue
        seen.add(sid)
        student = db.get(User, sid)
        if student is None or student.role != UserRole.student:
            skipped.append(sid)
            continue
        req = LeaveRequest(
            request_type=LeaveRequestType.od,
            category=category,
            student_id=student.id,
            section_id=student.section_id,
            title=payload.title,
            reason=payload.reason,
            event_name=payload.event_name,
            proof_url=payload.proof_url,
            start_date=payload.start_date,
            end_date=payload.end_date,
            status=LeaveStatus.approved,  # staff IS the approving authority
            applied_by_id=staff.id,
            reviewed_by_id=staff.id,
            review_note="Bulk OD raised by staff",
            reviewed_at=now,
            bulk_group_id=bulk_group_id,
        )
        db.add(req)
        created.append(req)
    db.commit()
    for req in created:
        db.refresh(req)
    return BulkODResult(
        bulk_group_id=bulk_group_id,
        created=len(created),
        skipped=skipped,
        entries=[_out(db, r) for r in created],
    )


@router.get("/me", response_model=list[LeaveRequestOut])
def my_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[LeaveRequestOut]:
    """All of the logged-in user's own leave/OD requests (newest first)."""
    reqs = db.scalars(
        select(LeaveRequest)
        .where(LeaveRequest.student_id == current_user.id)
        .order_by(LeaveRequest.created_at.desc())
    )
    return [_out(db, r) for r in reqs]


@router.get(
    "",
    response_model=list[LeaveRequestOut],
    dependencies=[Depends(staff_only)],
)
def list_requests(
    section_id: int | None = None,
    student_id: int | None = None,
    request_type: LeaveRequestType | None = None,
    status_filter: LeaveStatus | None = None,
    db: Session = Depends(get_db),
) -> list[LeaveRequestOut]:
    """Staff approval inbox: list/filter requests (pending first, then newest)."""
    stmt = select(LeaveRequest)
    if section_id is not None:
        stmt = stmt.where(LeaveRequest.section_id == section_id)
    if student_id is not None:
        stmt = stmt.where(LeaveRequest.student_id == student_id)
    if request_type is not None:
        stmt = stmt.where(LeaveRequest.request_type == request_type)
    if status_filter is not None:
        stmt = stmt.where(LeaveRequest.status == status_filter)
    reqs = list(db.scalars(stmt.order_by(LeaveRequest.created_at.desc())))
    # Pending bubbles to the top so the queue is actionable.
    reqs.sort(key=lambda r: 0 if r.status == LeaveStatus.pending else 1)
    return [_out(db, r) for r in reqs]


@router.get("/{request_id}", response_model=LeaveRequestOut)
def get_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LeaveRequestOut:
    """Open one request. A student may only read their own."""
    req = db.get(LeaveRequest, request_id)
    if req is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Request not found"
        )
    if not _is_staff(current_user) and req.student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to view this request",
        )
    return _out(db, req)


@router.patch("/{request_id}/decision", response_model=LeaveRequestOut)
def decide_request(
    request_id: int,
    payload: LeaveDecision,
    db: Session = Depends(get_db),
    staff: User = Depends(staff_only),
) -> LeaveRequestOut:
    """Approve or reject a PENDING request (teacher/admin)."""
    req = db.get(LeaveRequest, request_id)
    if req is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Request not found"
        )
    if req.status != LeaveStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Request is already {req.status.value}",
        )
    req.status = (
        LeaveStatus.approved
        if payload.status == "approved"
        else LeaveStatus.rejected
    )
    req.reviewed_by_id = staff.id
    req.review_note = payload.review_note
    req.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(req)
    return _out(db, req)


@router.post("/{request_id}/cancel", response_model=LeaveRequestOut)
def cancel_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LeaveRequestOut:
    """Withdraw a request. Only the applicant (or an admin) may cancel, and only
    while it is still pending or approved (not already rejected/cancelled)."""
    req = db.get(LeaveRequest, request_id)
    if req is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Request not found"
        )
    is_owner = (
        req.student_id == current_user.id
        or req.applied_by_id == current_user.id
    )
    if not is_owner and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to cancel this request",
        )
    if req.status in (LeaveStatus.rejected, LeaveStatus.cancelled):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Request is already {req.status.value}",
        )
    req.status = LeaveStatus.cancelled
    db.commit()
    db.refresh(req)
    return _out(db, req)


@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a request. The applicant may delete their own; admin any."""
    req = db.get(LeaveRequest, request_id)
    if req is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Request not found"
        )
    is_owner = (
        req.student_id == current_user.id
        or req.applied_by_id == current_user.id
    )
    if not is_owner and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to delete this request",
        )
    db.delete(req)
    db.commit()
