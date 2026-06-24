"""Attendance routes.

Role model (matches the product/prototype):
  * TEACHER marks (or re-marks) attendance for a section on a date, and views a
    section's records. In the product this is driven by face/class-photo
    auto-marking (AI worker, Phase 2.5); this endpoint is the foundation the
    AI worker will call. Admins do NOT mark attendance.
  * STUDENT views only their own records + summary.

Mounted under the `/attendance` prefix by `main.py`.
"""

from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db import get_db
from models import AttendanceRecord, AttendanceStatus, Section, User, UserRole
from schemas import (
    AttendanceMarkRequest,
    AttendanceRecordOut,
    AttendanceSummaryOut,
)
from security import get_current_user, require_roles

router = APIRouter(prefix="/attendance", tags=["attendance"])

# Attendance is a teacher's job (admins manage structure, not attendance).
teacher_only = require_roles(UserRole.teacher)


@router.post("/mark", response_model=list[AttendanceRecordOut])
def mark_attendance(
    payload: AttendanceMarkRequest,
    db: Session = Depends(get_db),
    teacher: User = Depends(teacher_only),
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
            existing.marked_by_id = teacher.id
            results.append(existing)
        else:
            record = AttendanceRecord(
                student_id=item.student_id,
                section_id=payload.section_id,
                date=payload.date,
                status=item.status,
                marked_by_id=teacher.id,
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


@router.get("/me", response_model=list[AttendanceRecordOut])
def my_attendance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AttendanceRecord]:
    """List the logged-in user's own attendance records (newest first)."""
    return list(
        db.scalars(
            select(AttendanceRecord)
            .where(AttendanceRecord.student_id == current_user.id)
            .order_by(AttendanceRecord.date.desc())
        )
    )


@router.get("/me/summary", response_model=AttendanceSummaryOut)
def my_attendance_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttendanceSummaryOut:
    """Aggregate the logged-in user's attendance into counts + a percentage."""
    records = list(
        db.scalars(
            select(AttendanceRecord).where(
                AttendanceRecord.student_id == current_user.id
            )
        )
    )
    total = len(records)
    present = sum(1 for r in records if r.status == AttendanceStatus.present)
    late = sum(1 for r in records if r.status == AttendanceStatus.late)
    absent = sum(1 for r in records if r.status == AttendanceStatus.absent)
    # Count 'late' as attended for the percentage.
    percentage = round((present + late) / total * 100, 2) if total else 0.0
    return AttendanceSummaryOut(
        total=total, present=present, absent=absent, late=late, percentage=percentage
    )


@router.get(
    "/section/{section_id}",
    response_model=list[AttendanceRecordOut],
    dependencies=[Depends(teacher_only)],
)
def section_attendance(
    section_id: int,
    date: date_type | None = None,
    db: Session = Depends(get_db),
) -> list[AttendanceRecord]:
    """List a section's attendance, optionally filtered by date (?date=YYYY-MM-DD).

    Teacher-only (this powers the teacher's attendance report screen).
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
    return list(db.scalars(stmt.order_by(AttendanceRecord.date.desc())))
