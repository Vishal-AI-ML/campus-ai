"""Multi-tenancy: institutes (tenants) & member invites (Step 36).

Admin-driven onboarding (no open self-signup):
  * A platform admin creates a tenant (institute).
  * An institute's admin/TPO invites users into THEIR OWN tenant by email,
    pre-assigning a role. This creates a single-use `tenant_invites` token.
  * The invited user opens the link and sets a name + password. That creates
    their account with the invite's tenant_id + role, marks the invite
    `accepted`, and auto-logs them in (a JWT is returned).

Why invite-only: the tenant always comes from the invite the admin issued, so
a user can never pick (or spoof) their own institute at signup.

Mounted under the `/tenants` prefix by `main.py`.
"""

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from rate_limit import limiter
from sqlalchemy import select
from sqlalchemy.orm import Session

from audit import record_audit
from db import get_db
from models import InviteStatus, Tenant, TenantInvite, User, UserRole
from schemas import (
    TenantAcceptInvite,
    TenantCreate,
    TenantInviteCreate,
    TenantInviteCreated,
    TenantInviteOut,
    TenantOut,
    Token,
)
from security import (
    create_access_token,
    hash_password,
    require_roles,
)

router = APIRouter(prefix="/tenants", tags=["tenants"])

# Platform admins onboard new institutes (tenants).
admin_only = require_roles(UserRole.admin)
# An institute's admin or TPO may invite members into their own tenant.
inviter_only = require_roles(UserRole.admin, UserRole.tpo)


def _generate_token() -> str:
    """Return a URL-safe, single-use invite token (~43 chars)."""
    return secrets.token_urlsafe(32)


@router.post("", response_model=TenantOut, status_code=status.HTTP_201_CREATED)
def create_tenant(
    payload: TenantCreate,
    current_user: User = Depends(admin_only),
    db: Session = Depends(get_db),
) -> Tenant:
    """Onboard a new institute (platform admin only)."""
    slug = payload.slug.lower().strip()
    if db.scalar(select(Tenant).where(Tenant.slug == slug)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A tenant with this slug already exists",
        )
    tenant = Tenant(name=payload.name.strip(), slug=slug)
    db.add(tenant)
    db.flush()  # assign tenant.id before auditing
    record_audit(
        db,
        current_user,
        "tenant.create",
        f"Created tenant '{tenant.name}' ({slug})",
        target_type="tenant",
        target_id=tenant.id,
    )
    db.commit()
    db.refresh(tenant)
    return tenant


@router.get(
    "",
    response_model=list[TenantOut],
    dependencies=[Depends(admin_only)],
)
def list_tenants(db: Session = Depends(get_db)) -> list[Tenant]:
    """List all tenants, newest first (platform admin)."""
    return list(db.scalars(select(Tenant).order_by(Tenant.created_at.desc())))


@router.post(
    "/invites",
    response_model=TenantInviteCreated,
    status_code=status.HTTP_201_CREATED,
)
def invite_member(
    payload: TenantInviteCreate,
    current_user: User = Depends(inviter_only),
    db: Session = Depends(get_db),
) -> TenantInviteCreated:
    """Invite a user into the caller's own institute, with a pre-set role."""
    if current_user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your account is not linked to a tenant.",
        )
    tenant = db.get(Tenant, current_user.tenant_id)
    if tenant is None or not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Your tenant was not found or is inactive.",
        )

    email = payload.email.lower().strip()
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )
    dup = db.scalar(
        select(TenantInvite).where(
            TenantInvite.email == email,
            TenantInvite.status == InviteStatus.pending,
        )
    )
    if dup is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A pending invite already exists for this email",
        )

    token = _generate_token()
    invite = TenantInvite(
        tenant_id=tenant.id,
        email=email,
        role=payload.role,
        token=token,
        status=InviteStatus.pending,
        invited_by_id=current_user.id,
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=payload.expires_in_days),
    )
    db.add(invite)
    record_audit(
        db,
        current_user,
        "tenant.invite",
        f"Invited {email} as {payload.role.value} to {tenant.name}",
        target_type="tenant",
        target_id=tenant.id,
    )
    db.commit()
    db.refresh(invite)
    db.refresh(tenant)
    return TenantInviteCreated(
        invite=TenantInviteOut.model_validate(invite),
        tenant=TenantOut.model_validate(tenant),
        token=token,
        accept_path=f"/accept-invite?token={token}",
    )


@router.post("/accept-invite", response_model=Token)
@limiter.limit("20/minute")
def accept_invite(
    request: Request,
    response: Response,
    payload: TenantAcceptInvite,
    db: Session = Depends(get_db),
) -> Token:
    """Accept a tenant invite: create the account & auto-login (public)."""
    invite = db.scalar(
        select(TenantInvite).where(TenantInvite.token == payload.token)
    )
    if invite is None or invite.status != InviteStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or already-used invite",
        )

    now = datetime.now(timezone.utc)
    expires = invite.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < now:
        invite.status = InviteStatus.expired
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invite has expired",
        )

    # The email must still be free (could have been registered meanwhile).
    if db.scalar(select(User).where(User.email == invite.email)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = User(
        email=invite.email,
        full_name=payload.full_name.strip(),
        hashed_password=hash_password(payload.password),
        role=invite.role,
        tenant_id=invite.tenant_id,
    )
    db.add(user)
    invite.status = InviteStatus.accepted
    invite.accepted_at = now
    db.commit()
    db.refresh(user)
    return Token(access_token=create_access_token(subject=str(user.id)))


@router.get("/invites", response_model=list[TenantInviteOut])
def list_invites(
    current_user: User = Depends(inviter_only),
    db: Session = Depends(get_db),
) -> list[TenantInvite]:
    """List invites for the caller's own tenant, newest first."""
    return list(
        db.scalars(
            select(TenantInvite)
            .where(TenantInvite.tenant_id == current_user.tenant_id)
            .order_by(TenantInvite.created_at.desc())
        )
    )


@router.post("/invites/{invite_id}/revoke", response_model=TenantInviteOut)
def revoke_invite(
    invite_id: int,
    current_user: User = Depends(inviter_only),
    db: Session = Depends(get_db),
) -> TenantInvite:
    """Revoke a still-pending invite in the caller's own tenant."""
    invite = db.get(TenantInvite, invite_id)
    if invite is None or invite.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found"
        )
    if invite.status != InviteStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending invites can be revoked",
        )
    invite.status = InviteStatus.revoked
    record_audit(
        db,
        current_user,
        "tenant.invite_revoke",
        f"Revoked tenant invite for {invite.email}",
        target_type="tenant_invite",
        target_id=invite.id,
    )
    db.commit()
    db.refresh(invite)
    return invite
