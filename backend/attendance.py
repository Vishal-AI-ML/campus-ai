"""Attendance routes.

  * Teachers/admins mark (or re-mark) attendance for a section on a date.
  * Students view their own records and a summary.
  * Teachers/admins view a section's records.

Mounted under the `/attendance` prefix by `main.py`.
"""

from datetime import date as date_type

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import ai_client
from db import get_db
from models import (
    AttendanceRecord,
    AttendanceStatus,
    FaceEnrollment,
    LeaveRequest,
    LeaveRequestType,
    LeaveStatus,
    Section,
    User,
    UserRole,
)
from schemas import (
    AttendanceMarkRequest,
    AttendanceRecordOut,
    AttendanceSummaryOut,
    FaceMatchOutsider,
    FaceMatchSuggestion,
    FacePhotoMatchRequest,
    FacePhotoMatchResponse,
)
from security import get_current_user, require_roles

router = APIRouter(prefix="/attendance", tags=["attendance"])

# Marking/reading a whole section is staff work (teacher or admin).
staff_only = require_roles(UserRole.teacher, UserRole.admin)

# --- Attendance condonation (approved leave / OD) --------------------------
# An approved OD (official duty) must NOT pull a student's attendance % down.
# Approved leave is condoned too, so an approved medical/personal absence does
# not wreck the percentage; narrow this to just {LeaveRequestType.od} if your
# institute counts personal leave as a real absence.
CONDONING_TYPES = {LeaveRequestType.od, LeaveRequestType.leave}


def _approved_ranges_for(
    db: Session, student_ids: list[int]
) -> dict[int, list[LeaveRequest]]:
    """Map each student id -> their approved, condoning leave/OD requests."""
    ids = list({sid for sid in student_ids})
    if not ids:
        return {}
    rows = db.scalars(
        select(LeaveRequest).where(
            LeaveRequest.student_id.in_(ids),
            LeaveRequest.status == LeaveStatus.approved,
            LeaveRequest.request_type.in_(list(CONDONING_TYPES)),
        )
    )
    ranges: dict[int, list[LeaveRequest]] = {}
    for r in rows:
        ranges.setdefault(r.student_id, []).append(r)
    return ranges


def _covering_request(
    ranges: list[LeaveRequest], on_date: date_type
) -> LeaveRequest | None:
    """First approved leave/OD whose [start, end] covers `on_date`, else None."""
    for r in ranges:
        if r.start_date <= on_date <= r.end_date:
            return r
    return None


def _condone_label(req: LeaveRequest) -> str:
    """Short human reason, e.g. 'OD: Spring Fest' or 'Leave: medical'."""
    kind = "OD" if req.request_type == LeaveRequestType.od else "Leave"
    name = req.event_name or req.title or req.category
    return f"{kind}: {name}"


def _record_out(
    rec: AttendanceRecord, ranges: list[LeaveRequest]
) -> AttendanceRecordOut:
    """Build a record output, flagging condoned absences (approved leave/OD)."""
    covering = (
        _covering_request(ranges, rec.date)
        if rec.status == AttendanceStatus.absent
        else None
    )
    return AttendanceRecordOut(
        id=rec.id,
        student_id=rec.student_id,
        section_id=rec.section_id,
        date=rec.date,
        status=rec.status,
        condoned=covering is not None,
        condone_reason=_condone_label(covering) if covering else None,
    )


@router.post("/mark", response_model=list[AttendanceRecordOut])
def mark_attendance(
    payload: AttendanceMarkRequest,
    db: Session = Depends(get_db),
    staff: User = Depends(staff_only),
) -> list[AttendanceRecord]:
    """Create or update attendance rows for the given section + date.

    Re-marking the same student/section/date updates the existing row, so this
    endpoint is safe to call repeatedly (idempotent per student).
    """
    section = db.get(Section, payload.section_id)
    if section is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Section not found"
        )

    results: list[AttendanceRecord] = []
    for item in payload.records:
        existing = db.scalar(
            select(AttendanceRecord).where(
                AttendanceRecord.student_id == item.student_id,
                AttendanceRecord.section_id == payload.section_id,
                AttendanceRecord.date == payload.date,
            )
        )
        if existing is not None:
            existing.status = item.status
            existing.marked_by_id = staff.id
            results.append(existing)
        else:
            record = AttendanceRecord(
                student_id=item.student_id,
                section_id=payload.section_id,
                date=payload.date,
                status=item.status,
                marked_by_id=staff.id,
            )
            db.add(record)
            results.append(record)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more student_id values are invalid",
        )

    for record in results:
        db.refresh(record)
    return results


@router.post("/photo", response_model=FacePhotoMatchResponse)
def match_class_photo(
    payload: FacePhotoMatchRequest,
    db: Session = Depends(get_db),
    staff: User = Depends(staff_only),
) -> FacePhotoMatchResponse:
    """Match a class photo against a section's enrolled students (teacher/admin).

    This only SUGGESTS who is present - it never writes attendance. The worker
    detects every face and matches each against the enrolled embeddings; we
    turn that into a per-student suggestion over THIS section's roster. The
    teacher reviews/edits the suggestions and confirms by calling
    POST /attendance/mark - keeping a human in the loop (moat-consistent).
    """
    section = db.get(Section, payload.section_id)
    if section is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Section not found"
        )

    try:
        result = ai_client.match_faces(
            payload.image_base64, payload.score_threshold
        )
    except httpx.HTTPStatusError as exc:
        detail = "Face worker rejected the request."
        try:
            detail = exc.response.json().get("detail", detail)
        except Exception:  # noqa: BLE001 - fall back to the generic message
            pass
        raise HTTPException(status_code=exc.response.status_code, detail=detail)
    except Exception:  # noqa: BLE001 - any transport failure => worker down
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI face worker is unavailable. Make sure it is running on :8100.",
        )

    # Worker matches: student_id -> best cosine score (across all enrolled).
    matched_by_id: dict[int, float] = {
        int(m["student_id"]): float(m["score"]) for m in result.get("matched", [])
    }

    # This section's roster + which of them are enrolled.
    roster = list(
        db.scalars(
            select(User)
            .where(User.role == UserRole.student)
            .where(User.section_id == payload.section_id)
            .order_by(User.full_name)
        )
    )
    roster_ids = {s.id for s in roster}
    enrolled_ids = {
        e.student_id
        for e in db.scalars(
            select(FaceEnrollment).where(
                FaceEnrollment.student_id.in_(list(roster_ids) or [0])
            )
        )
    }

    suggestions = [
        FaceMatchSuggestion(
            student_id=s.id,
            full_name=s.full_name,
            enrolled=s.id in enrolled_ids,
            matched=s.id in matched_by_id,
            score=round(matched_by_id[s.id], 4) if s.id in matched_by_id else None,
            suggested_status=(
                AttendanceStatus.present
                if s.id in matched_by_id
                else AttendanceStatus.absent
            ),
        )
        for s in roster
    ]

    # Enrolled students matched in the photo but NOT part of this section (e.g.
    # someone from another class in frame) - surfaced for the teacher's
    # awareness, never auto-marked here.
    outside = [
        FaceMatchOutsider(student_id=sid, score=round(score, 4))
        for sid, score in matched_by_id.items()
        if sid not in roster_ids
    ]

    return FacePhotoMatchResponse(
        section_id=payload.section_id,
        detected_faces=int(result.get("detected_faces", 0)),
        unmatched_faces=int(result.get("unmatched_faces", 0)),
        threshold=float(result.get("threshold", 0.0)),
        suggestions=suggestions,
        matched_outside_section=outside,
    )


@router.get("/me", response_model=list[AttendanceRecordOut])
def my_attendance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AttendanceRecordOut]:
    """List the logged-in user's own attendance records (newest first).

    Absences inside an approved leave/OD are flagged `condoned` so the UI can
    show an "Excused" badge instead of a plain absence.
    """
    records = list(
        db.scalars(
            select(AttendanceRecord)
            .where(AttendanceRecord.student_id == current_user.id)
            .order_by(AttendanceRecord.date.desc())
        )
    )
    ranges = _approved_ranges_for(db, [current_user.id]).get(current_user.id, [])
    return [_record_out(r, ranges) for r in records]


@router.get("/me/summary", response_model=AttendanceSummaryOut)
def my_attendance_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttendanceSummaryOut:
    """Aggregate the logged-in user's attendance into counts + a percentage.

    Absences covered by an approved leave/OD are *condoned*: counted as
    `excused` and removed from the percentage denominator, so official duty
    (and approved leave) never pulls the student's attendance % down. We also
    return `raw_percentage` (before condonation) for full transparency.
    """
    records = list(
        db.scalars(
            select(AttendanceRecord).where(
                AttendanceRecord.student_id == current_user.id
            )
        )
    )
    ranges = _approved_ranges_for(db, [current_user.id]).get(current_user.id, [])

    total = len(records)
    present = late = absent = excused = 0
    for r in records:
        if r.status == AttendanceStatus.absent and _covering_request(
            ranges, r.date
        ):
            excused += 1
            continue
        if r.status == AttendanceStatus.present:
            present += 1
        elif r.status == AttendanceStatus.late:
            late += 1
        else:  # absent (not condoned)
            absent += 1

    # 'late' counts as attended; condoned absences leave the denominator.
    effective = total - excused
    attended = present + late
    percentage = round(attended / effective * 100, 2) if effective else 0.0
    raw_percentage = round(attended / total * 100, 2) if total else 0.0
    return AttendanceSummaryOut(
        total=total,
        present=present,
        absent=absent,
        late=late,
        excused=excused,
        percentage=percentage,
        raw_percentage=raw_percentage,
    )


@router.get(
    "/section/{section_id}",
    response_model=list[AttendanceRecordOut],
    dependencies=[Depends(staff_only)],
)
def section_attendance(
    section_id: int,
    date: date_type | None = None,
    db: Session = Depends(get_db),
) -> list[AttendanceRecordOut]:
    """List a section's attendance, optionally filtered by date (?date=YYYY-MM-DD).

    Each record is annotated with `condoned` so staff can see at a glance which
    absences are excused by an approved leave/OD.
    """
    section = db.get(Section, section_id)
    if section is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Section not found"
        )
    stmt = select(AttendanceRecord).where(
        AttendanceRecord.section_id == section_id
    )
    if date is not None:
        stmt = stmt.where(AttendanceRecord.date == date)
    records = list(db.scalars(stmt.order_by(AttendanceRecord.date.desc())))
    ranges_by_student = _approved_ranges_for(
        db, [r.student_id for r in records]
    )
    return [
        _record_out(r, ranges_by_student.get(r.student_id, []))
        for r in records
    ]
