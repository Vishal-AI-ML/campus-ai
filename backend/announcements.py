"""Announcements: institute-wide broadcasts posted by admins.

Admins post an announcement targeted at everyone ("all") or a single role
("student" | "teacher" | "tpo"). Every authenticated user can list the
announcements meant for them (audience "all" or their own role), newest first.

Reads are open to any logged-in user; posting and deleting are admin-only
(governance). Mounted under the `/announcements` prefix by `main.py`.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from db import get_db
from models import Announcement, User, UserRole
from schemas import AnnouncementCreate, AnnouncementOut
from security import get_current_user, require_roles

router = APIRouter(prefix="/announcements", tags=["announcements"])

# Posting / removing announcements is an admin (governance) action.
admin_only = require_roles(UserRole.admin)


@router.post(
    "",
    response_model=AnnouncementOut,
    status_code=status.HTTP_201_CREATED,
)
def create_announcement(
    payload: AnnouncementCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
) -> Announcement:
    """Post an announcement (admin). Targets everyone or a single role."""
    announcement = Announcement(
        title=payload.title,
        body=payload.body,
        audience=payload.audience,
        author_id=admin.id,
    )
    db.add(announcement)
    db.commit()
    db.refresh(announcement)
    return announcement


@router.get("", response_model=list[AnnouncementOut])
def list_announcements(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Announcement]:
    """List announcements visible to the caller, newest first.

    Admins see every announcement (a governance / management view); everyone
    else sees only posts targeted at them (audience "all" or their own role).
    """
    stmt = select(Announcement).order_by(Announcement.created_at.desc())
    if current_user.role != UserRole.admin:
        stmt = stmt.where(
            or_(
                Announcement.audience == "all",
                Announcement.audience == current_user.role.value,
            )
        )
    return list(db.scalars(stmt))


@router.delete("/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(admin_only),
) -> None:
    """Delete an announcement (admin)."""
    announcement = db.get(Announcement, announcement_id)
    if announcement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Announcement not found",
        )
    db.delete(announcement)
    db.commit()
