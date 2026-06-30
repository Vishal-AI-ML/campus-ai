"""Marketing & feedback routes: public lead capture + in-product feedback.

  * Lead     -> public, unauthenticated submissions from the marketing site's
                contact / demo-request form (POST /leads).
  * Feedback -> anonymous in-product feedback (POST /feedback).
  * Admins review both (GET /leads, GET /feedback) and mark a lead handled.

The public POST routes intentionally have NO auth dependency - prospects are
not users yet. Admin reads are gated by `require_roles(UserRole.admin)`.
This router uses explicit full paths (no prefix) so /leads and /feedback are
both top-level. Wired into the app by `main.py`.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from db import get_db
from models import Feedback, Lead, User, UserRole
from schemas import FeedbackCreate, FeedbackOut, LeadCreate, LeadOut
from security import require_roles

from rate_limit import limiter

router = APIRouter(tags=["marketing"])

# Reusable dependency: only admins may review captured leads/feedback.
admin_only = require_roles(UserRole.admin)


# --- Public: capture a lead (marketing contact form) -----------------------
@router.post("/leads", response_model=LeadOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def create_lead(
    request: Request,
    response: Response,
    payload: LeadCreate,
    db: Session = Depends(get_db),
) -> Lead:
    """Public demo-request/contact submission. No authentication required."""
    lead = Lead(
        name=payload.name,
        email=payload.email,
        institute=payload.institute,
        role=payload.role,
        message=payload.message,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


# --- Public: in-product feedback -------------------------------------------
@router.post(
    "/feedback", response_model=FeedbackOut, status_code=status.HTTP_201_CREATED
)
@limiter.limit("20/minute")
def create_feedback(
    request: Request,
    response: Response,
    payload: FeedbackCreate,
    db: Session = Depends(get_db),
) -> Feedback:
    """Submit anonymous feedback. Stored without a user link."""
    entry = Feedback(
        message=payload.message,
        category=payload.category,
        rating=payload.rating,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


# --- Admin: review captured leads ------------------------------------------
@router.get("/leads", response_model=list[LeadOut])
def list_leads(
    handled: bool | None = None,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
) -> list[Lead]:
    """List captured leads (admin).

    Leads are platform-wide, pre-signup submissions: an admin sees every
    still-unclaimed lead (tenant_id IS NULL) plus the leads already claimed
    into their own institute. Optionally filter by handled state.
    """
    stmt = (
        select(Lead)
        .where((Lead.tenant_id.is_(None)) | (Lead.tenant_id == admin.tenant_id))
        .order_by(Lead.created_at.desc())
    )
    if handled is not None:
        stmt = stmt.where(Lead.handled == handled)
    return list(db.scalars(stmt))


@router.patch("/leads/{lead_id}/handled", response_model=LeadOut)
def mark_lead_handled(
    lead_id: int,
    handled: bool = True,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
) -> Lead:
    """Mark a lead as handled / not handled (admin).

    An admin may only touch unclaimed leads or leads in their own institute.
    """
    lead = db.get(Lead, lead_id)
    if lead is None or (
        lead.tenant_id is not None and lead.tenant_id != admin.tenant_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found"
        )
    lead.handled = handled
    db.commit()
    db.refresh(lead)
    return lead


@router.patch("/leads/{lead_id}/claim", response_model=LeadOut)
def claim_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
) -> Lead:
    """Link an unclaimed lead to the admin's institute ("link later").

    Pre-signup leads land with no tenant; once an institute owns the
    relationship an admin claims the lead into their own tenant. Only a
    still-unclaimed lead (or one already in the admin's tenant) can be
    claimed - another institute's lead returns 404.
    """
    lead = db.get(Lead, lead_id)
    if lead is None or (
        lead.tenant_id is not None and lead.tenant_id != admin.tenant_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found"
        )
    lead.tenant_id = admin.tenant_id
    db.commit()
    db.refresh(lead)
    return lead


# --- Admin: review submitted feedback --------------------------------------
@router.get("/feedback", response_model=list[FeedbackOut])
def list_feedback(
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
) -> list[Feedback]:
    """List submitted feedback, newest first (admin).

    Same visibility rule as leads: unclaimed (NULL-tenant) feedback plus the
    admin's own institute.
    """
    stmt = (
        select(Feedback)
        .where(
            (Feedback.tenant_id.is_(None))
            | (Feedback.tenant_id == admin.tenant_id)
        )
        .order_by(Feedback.created_at.desc())
    )
    return list(db.scalars(stmt))
