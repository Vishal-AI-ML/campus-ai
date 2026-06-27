"""Timetable module.

A section's weekly class schedule, modelled as recurring weekly slots (the same
timetable repeats every week). One row = one class period for a section on a
given weekday, optionally tied to a subject and a teacher.

  * STAFF (teacher/admin) CREATE / UPDATE / DELETE slots.
      - admin may delete any slot; a teacher may delete only slots they created.
  * STUDENT reads their OWN section's weekly timetable  -> GET /timetable/me
  * TEACHER reads their personal teaching schedule       -> GET /timetable/teaching
  * STAFF reads any section's grid                        -> GET /timetable?section_id=

`day_of_week` is 0=Monday .. 6=Sunday. Results are always sorted by
(day_of_week, start_time) so the frontend can render a clean weekly grid.
Mounted under the `/timetable` prefix by `main.py`.
"""

from datetime import time

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from db import get_db
from models import Section, Subject, TimetableEntry, User, UserRole
from schemas import (
    TimetableEntryCreate,
    TimetableEntryOut,
    TimetableEntryUpdate,
)
from security import get_current_user, require_roles

router = APIRouter(prefix="/timetable", tags=["timetable"])

# Creating / editing / deleting the timetable is staff work (teacher or admin).
staff_only = require_roles(UserRole.teacher, UserRole.admin)

# Roles treated as "staff" for section-access checks (may reach any section).
STAFF_ROLES = (UserRole.teacher, UserRole.admin, UserRole.tpo)


def _is_staff(user: User) -> bool:
    return user.role in STAFF_ROLES


def _validate_times(start: time, end: time) -> None:
    """A slot must end strictly after it starts."""
    if end <= start:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_time must be later than start_time",
        )


def _validate_teacher(db: Session, teacher_id: int | None) -> None:
    """If a teacher is assigned to the slot, they must exist and be staff."""
    if teacher_id is None:
        return
    teacher = db.get(User, teacher_id)
    if teacher is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found"
        )
    if teacher.role not in (UserRole.teacher, UserRole.admin):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Assigned user is not a teacher",
        )


def _check_slot_free(
    db: Session,
    section_id: int,
    day_of_week: int,
    start_time: time,
    exclude_id: int | None = None,
) -> None:
    """Reject a duplicate slot (same section + weekday + start time)."""
    stmt = select(TimetableEntry).where(
        TimetableEntry.section_id == section_id,
        TimetableEntry.day_of_week == day_of_week,
        TimetableEntry.start_time == start_time,
    )
    if exclude_id is not None:
        stmt = stmt.where(TimetableEntry.id != exclude_id)
    if db.scalar(stmt) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A slot already starts at this time on this day for this section",
        )


def _entry_out(db: Session, entry: TimetableEntry) -> TimetableEntryOut:
    """Build a TimetableEntryOut enriched with display names."""
    section = db.get(Section, entry.section_id)
    subject = db.get(Subject, entry.subject_id) if entry.subject_id else None
    teacher = db.get(User, entry.teacher_id) if entry.teacher_id else None
    return TimetableEntryOut(
        id=entry.id,
        section_id=entry.section_id,
        section_name=section.name if section else None,
        subject_id=entry.subject_id,
        subject_name=subject.name if subject else None,
        teacher_id=entry.teacher_id,
        teacher_name=teacher.full_name if teacher else None,
        day_of_week=entry.day_of_week,
        start_time=entry.start_time,
        end_time=entry.end_time,
        room=entry.room,
    )


@router.post(
    "", response_model=TimetableEntryOut, status_code=status.HTTP_201_CREATED
)
def create_entry(
    payload: TimetableEntryCreate,
    db: Session = Depends(get_db),
    staff: User = Depends(staff_only),
) -> TimetableEntryOut:
    """Add a recurring weekly class slot to a section's timetable."""
    if db.get(Section, payload.section_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Section not found"
        )
    if (
        payload.subject_id is not None
        and db.get(Subject, payload.subject_id) is None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found"
        )
    _validate_teacher(db, payload.teacher_id)
    _validate_times(payload.start_time, payload.end_time)
    _check_slot_free(
        db, payload.section_id, payload.day_of_week, payload.start_time
    )
    entry = TimetableEntry(
        section_id=payload.section_id,
        subject_id=payload.subject_id,
        teacher_id=payload.teacher_id,
        day_of_week=payload.day_of_week,
        start_time=payload.start_time,
        end_time=payload.end_time,
        room=payload.room,
        created_by_id=staff.id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _entry_out(db, entry)


@router.get(
    "",
    response_model=list[TimetableEntryOut],
    dependencies=[Depends(staff_only)],
)
def list_entries(
    section_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[TimetableEntryOut]:
    """List timetable slots (staff), optionally filtered by section."""
    stmt = select(TimetableEntry)
    if section_id is not None:
        stmt = stmt.where(TimetableEntry.section_id == section_id)
    entries = db.scalars(
        stmt.order_by(TimetableEntry.day_of_week, TimetableEntry.start_time)
    )
    return [_entry_out(db, e) for e in entries]


@router.get("/me", response_model=list[TimetableEntryOut])
def my_timetable(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TimetableEntryOut]:
    """The weekly timetable for the logged-in user's own section."""
    if current_user.section_id is None:
        return []
    entries = db.scalars(
        select(TimetableEntry)
        .where(TimetableEntry.section_id == current_user.section_id)
        .order_by(TimetableEntry.day_of_week, TimetableEntry.start_time)
    )
    return [_entry_out(db, e) for e in entries]


@router.get("/teaching", response_model=list[TimetableEntryOut])
def my_teaching_schedule(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TimetableEntryOut]:
    """The personal teaching schedule for the logged-in teacher (across sections)."""
    entries = db.scalars(
        select(TimetableEntry)
        .where(TimetableEntry.teacher_id == current_user.id)
        .order_by(TimetableEntry.day_of_week, TimetableEntry.start_time)
    )
    return [_entry_out(db, e) for e in entries]


@router.get("/{entry_id}", response_model=TimetableEntryOut)
def get_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TimetableEntryOut:
    """Open a single slot. Students may only read their own section's."""
    entry = db.get(TimetableEntry, entry_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Timetable entry not found"
        )
    if not _is_staff(current_user) and entry.section_id != current_user.section_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to view this timetable entry",
        )
    return _entry_out(db, entry)


@router.patch("/{entry_id}", response_model=TimetableEntryOut)
def update_entry(
    entry_id: int,
    payload: TimetableEntryUpdate,
    db: Session = Depends(get_db),
    staff: User = Depends(staff_only),
) -> TimetableEntryOut:
    """Edit a slot. Admins may edit any; teachers only slots they created."""
    entry = db.get(TimetableEntry, entry_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Timetable entry not found"
        )
    if staff.role != UserRole.admin and entry.created_by_id != staff.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit slots you created",
        )
    data = payload.model_dump(exclude_unset=True)
    if "subject_id" in data and data["subject_id"] is not None:
        if db.get(Subject, data["subject_id"]) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found"
            )
    if "teacher_id" in data:
        _validate_teacher(db, data["teacher_id"])
    new_day = data.get("day_of_week", entry.day_of_week)
    new_start = data.get("start_time", entry.start_time)
    new_end = data.get("end_time", entry.end_time)
    _validate_times(new_start, new_end)
    if new_day != entry.day_of_week or new_start != entry.start_time:
        _check_slot_free(
            db, entry.section_id, new_day, new_start, exclude_id=entry.id
        )
    for field, value in data.items():
        setattr(entry, field, value)
    db.commit()
    db.refresh(entry)
    return _entry_out(db, entry)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    staff: User = Depends(staff_only),
) -> None:
    """Delete a slot. Admins can delete any; teachers only their own."""
    entry = db.get(TimetableEntry, entry_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Timetable entry not found"
        )
    if staff.role != UserRole.admin and entry.created_by_id != staff.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete slots you created",
        )
    db.delete(entry)
    db.commit()
