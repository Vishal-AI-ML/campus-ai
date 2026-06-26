"""Audit log: append-only trail of governance actions.

`record_audit()` is a small helper that other routers call after a sensitive
change (role/status change, structure edits, etc.). It writes one `audit_logs`
row describing who did what. Reads are admin-only via `GET /audit`.

The helper only *adds* the row to the caller's session (it does not commit), so
it must be called just before the caller's own `db.commit()`. That way the
audit row and the change it records are saved atomically in one transaction:
if the caller rolls back, the audit entry is discarded too, keeping the trail
consistent with what actually happened.

Mounted under the `/audit` prefix by `main.py`.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from db import get_db
from models import AuditLog, User, UserRole
from schemas import AuditLogOut
from security import require_roles

router = APIRouter(prefix="/audit", tags=["audit"])

# Only admins may read the governance trail.
admin_only = require_roles(UserRole.admin)


def record_audit(
    db: Session,
    actor: User | None,
    action: str,
    summary: str,
    target_type: str | None = None,
    target_id: str | int | None = None,
) -> None:
    """Add one audit row to the current transaction (the caller commits).

    Call this *before* the caller's `db.commit()` so the audit row and the
    change it describes are persisted together.
    """
    db.add(
        AuditLog(
            actor_id=actor.id if actor is not None else None,
            actor_email=actor.email if actor is not None else None,
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id is not None else None,
            summary=summary,
        )
    )


@router.get(
    "", response_model=list[AuditLogOut], dependencies=[Depends(admin_only)]
)
def list_audit(
    action: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[AuditLog]:
    """List recent audit entries, newest first (admin only).

    Optional ?action= filters by exact action key (e.g. "user.role_change").
    """
    stmt = select(AuditLog).order_by(
        AuditLog.created_at.desc(), AuditLog.id.desc()
    )
    if action:
        stmt = stmt.where(AuditLog.action == action)
    stmt = stmt.limit(max(1, min(limit, 500)))
    return list(db.scalars(stmt))
