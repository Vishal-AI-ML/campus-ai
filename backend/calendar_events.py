"""Academic calendar: institute events posted by admins.

Admins add calendar entries - holiday / exam / event / deadline - targeted at
everyone ("all") or a single role ("student" | "teacher" | "tpo"). Every
authenticated user lists the entries meant for them (audience "all" or their
own role); admins see all (a governance / management view).

Reads are open to any logged-in user; posting and deleting are admin-only.
Mounted under the `/calendar` prefix by `main.py`.

Named `calendar_events.py` (not `calendar.py`) so it does not shadow Python's
standard-library `calendar` module.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from db import get_db
from models import CalendarEvent, User, UserRole
from schemas import CalendarEventCreate, CalendarEventOut
from security import get_current_user, require_roles

router = APIRouter(prefix="/calendar", tags=["calendar"])

# Posting / removing calendar entries is an admin (governance) action.
admin_only = require_roles(UserRole.admin)


@router.post(
    "",
    response_model=CalendarEventOut,
    status_code=status.HTTP_201_CREATED,
)
def create_event(
    payload: CalendarEventCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
) -> CalendarEvent:
    """Add a calendar entry (admin). Targets everyone or a single role."""
    if payload.end_date is not None and payload.end_date < payload.event_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date cannot be before event_date",
        )
    event = CalendarEvent(
        title=payload.title,
        description=payload.description,
        event_date=payload.event_date,
        end_date=payload.end_date,
        category=payload.category,
        audience=payload.audience,
        created_by_id=admin.id,
        tenant_id=admin.tenant_id,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("", response_model=list[CalendarEventOut])
def list_events(
    upcoming: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CalendarEvent]:
    """List calendar entries visible to the caller, soonest first.

    Admins see every entry; everyone else sees only entries targeted at them
    (audience "all" or their own role). Pass ?upcoming=true to hide entries
    whose date is already in the past.
    """
    stmt = select(CalendarEvent).where(
        CalendarEvent.tenant_id == current_user.tenant_id
    )
    if current_user.role != UserRole.admin:
        stmt = stmt.where(
            or_(
                CalendarEvent.audience == "all",
                CalendarEvent.audience == current_user.role.value,
            )
        )
    if upcoming:
        stmt = stmt.where(CalendarEvent.event_date >= date.today())
    stmt = stmt.order_by(CalendarEvent.event_date.asc())
    return list(db.scalars(stmt))


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
) -> None:
    """Delete a calendar entry (admin)."""
    event = db.get(CalendarEvent, event_id)
    if event is None or event.tenant_id != admin.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calendar event not found",
        )
    db.delete(event)
    db.commit()
