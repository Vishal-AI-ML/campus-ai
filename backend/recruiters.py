"""Recruiter portal - onboarding & external recruiter accounts (Step 27.1).

This is the FIRST external-facing module: companies that recruit from the
institute. The TPO stays fully in control of who gets in.

Flow:
  * The TPO onboards a company and invites its first HR by email. This creates
    a `recruiters` company row (status `pending`) plus a single-use
    `recruiter_invites` token (the link the recruiter will use).
  * The recruiter opens the invite link and sets a name + password. That
    creates their login account (role `recruiter`), links it to the company
    via `recruiter_users`, marks the invite `accepted`, and flips the company
    to `active`. They are auto-logged-in (a JWT is returned).
  * A recruiter can read their OWN company profile via `/recruiters/me`.

Strict scoping: a recruiter only ever sees their own company. Candidate
viewing, decisions and offers come in later sub-steps (27.2 / 27.3).

Mounted under the `/recruiters` prefix by `main.py`.
"""

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from rate_limit import limiter
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from audit import record_audit
from db import get_db
from models import (
    Application,
    ApplicationStatus,
    Drive,
    InviteStatus,
    Offer,
    OfferStatus,
    Recruiter,
    RecruiterDecision,
    RecruiterInvite,
    RecruiterStatus,
    RecruiterUser,
    User,
    UserRole,
)
from placement import _student_profile
from schemas import (
    ApplicationOut,
    ContactRevealUpdate,
    DriveOut,
    DriveRecruiterLink,
    OfferCreate,
    OfferOut,
    OfferRespond,
    RecruiterAcceptInvite,
    RecruiterCandidateOut,
    RecruiterDecisionUpdate,
    RecruiterDriveOut,
    RecruiterInviteCreate,
    RecruiterInviteCreated,
    RecruiterInviteOut,
    RecruiterMeOut,
    RecruiterOut,
    Token,
    UserOut,
)
from security import (
    create_access_token,
    get_current_user,
    hash_password,
    require_roles,
)

router = APIRouter(prefix="/recruiters", tags=["recruiters"])

# Only the TPO (or admin) may onboard companies and manage invites.
staff_only = require_roles(UserRole.tpo, UserRole.admin)
# Only an external recruiter account may read its own company profile.
recruiter_only = require_roles(UserRole.recruiter)


def _generate_token() -> str:
    """Return a URL-safe, single-use invite token (~43 chars)."""
    return secrets.token_urlsafe(32)


@router.post(
    "/invite",
    response_model=RecruiterInviteCreated,
    status_code=status.HTTP_201_CREATED,
)
def invite_recruiter(
    payload: RecruiterInviteCreate,
    current_user: User = Depends(staff_only),
    db: Session = Depends(get_db),
) -> RecruiterInviteCreated:
    """Onboard a company and create a single-use invite for its first HR (TPO)."""
    email = payload.email.lower().strip()

    # The email must not already belong to an account.
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )
    # ...nor have an outstanding pending invite.
    dup = db.scalar(
        select(RecruiterInvite).where(
            RecruiterInvite.email == email,
            RecruiterInvite.status == InviteStatus.pending,
        )
    )
    if dup is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A pending invite already exists for this email",
        )

    company = Recruiter(
        company_name=payload.company_name.strip(),
        website=payload.website,
        about=payload.about,
        status=RecruiterStatus.pending,
        created_by_id=current_user.id,
    )
    db.add(company)
    db.flush()  # assign company.id before linking the invite

    token = _generate_token()
    invite = RecruiterInvite(
        recruiter_id=company.id,
        email=email,
        token=token,
        status=InviteStatus.pending,
        title=payload.title,
        invited_by_id=current_user.id,
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=payload.expires_in_days),
    )
    db.add(invite)
    record_audit(
        db,
        current_user,
        "recruiter.invite",
        f"Invited {email} as recruiter for {company.company_name}",
        target_type="recruiter",
        target_id=company.id,
    )
    db.commit()
    db.refresh(invite)
    db.refresh(company)

    return RecruiterInviteCreated(
        invite=RecruiterInviteOut.model_validate(invite),
        recruiter=RecruiterOut.model_validate(company),
        token=token,
        accept_path=f"/recruiter/accept-invite?token={token}",
    )


@router.post("/accept-invite", response_model=Token)
@limiter.limit("20/minute")
def accept_invite(
    request: Request,
    response: Response,
    payload: RecruiterAcceptInvite,
    db: Session = Depends(get_db),
) -> Token:
    """Accept an invite: create the recruiter account & auto-login (public)."""
    invite = db.scalar(
        select(RecruiterInvite).where(RecruiterInvite.token == payload.token)
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
        role=UserRole.recruiter,
    )
    db.add(user)
    db.flush()  # assign user.id before linking

    db.add(
        RecruiterUser(
            recruiter_id=invite.recruiter_id,
            user_id=user.id,
            title=invite.title,
            is_primary=True,
        )
    )
    invite.status = InviteStatus.accepted
    invite.accepted_at = now

    company = db.get(Recruiter, invite.recruiter_id)
    if company is not None:
        company.status = RecruiterStatus.active

    db.commit()
    db.refresh(user)
    return Token(access_token=create_access_token(subject=str(user.id)))


@router.get(
    "",
    response_model=list[RecruiterOut],
    dependencies=[Depends(staff_only)],
)
def list_recruiters(db: Session = Depends(get_db)) -> list[Recruiter]:
    """List all onboarded recruiter companies, newest first (TPO/admin)."""
    return list(
        db.scalars(select(Recruiter).order_by(Recruiter.created_at.desc()))
    )


@router.get(
    "/invites",
    response_model=list[RecruiterInviteOut],
    dependencies=[Depends(staff_only)],
)
def list_invites(db: Session = Depends(get_db)) -> list[RecruiterInvite]:
    """List recruiter invites, newest first (TPO/admin)."""
    return list(
        db.scalars(
            select(RecruiterInvite).order_by(RecruiterInvite.created_at.desc())
        )
    )


@router.post("/invites/{invite_id}/revoke", response_model=RecruiterInviteOut)
def revoke_invite(
    invite_id: int,
    current_user: User = Depends(staff_only),
    db: Session = Depends(get_db),
) -> RecruiterInvite:
    """Revoke a still-pending invite so its token can no longer be used (TPO)."""
    invite = db.get(RecruiterInvite, invite_id)
    if invite is None:
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
        "recruiter.invite_revoke",
        f"Revoked recruiter invite for {invite.email}",
        target_type="recruiter_invite",
        target_id=invite.id,
    )
    db.commit()
    db.refresh(invite)
    return invite


@router.get("/me", response_model=RecruiterMeOut)
def read_my_recruiter(
    current_user: User = Depends(recruiter_only),
    db: Session = Depends(get_db),
) -> RecruiterMeOut:
    """Return the logged-in recruiter's account + their company profile."""
    link = db.scalar(
        select(RecruiterUser).where(RecruiterUser.user_id == current_user.id)
    )
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No recruiter profile linked to this account",
        )
    company = db.get(Recruiter, link.recruiter_id)
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recruiter company not found",
        )
    return RecruiterMeOut(
        user=UserOut.model_validate(current_user),
        recruiter=RecruiterOut.model_validate(company),
        title=link.title,
        is_primary=link.is_primary,
    )


# --- Candidate viewing (Step 27.2) -----------------------------------------
def _recruiter_for_user(db: Session, user: User) -> tuple[RecruiterUser, Recruiter]:
    """Resolve the company a recruiter account belongs to (strict scoping)."""
    link = db.scalar(
        select(RecruiterUser).where(RecruiterUser.user_id == user.id)
    )
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This recruiter account is not linked to any company.",
        )
    recruiter = db.get(Recruiter, link.recruiter_id)
    if recruiter is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Company not found"
        )
    if recruiter.status == RecruiterStatus.suspended:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your company's access has been suspended.",
        )
    return link, recruiter


# Candidates are exposed to recruiters ONLY once the TPO has acted on them:
# shortlisted or selected. 'applied' and 'rejected' stay invisible.
_VISIBLE_TO_RECRUITER = (
    ApplicationStatus.shortlisted,
    ApplicationStatus.selected,
)


def _candidate_out(
    db: Session, application: Application, drive: Drive
) -> RecruiterCandidateOut:
    """Build a recruiter-facing candidate card from one application.

    The verified-data snapshot is always shown; contact (email) is included
    ONLY when the TPO has revealed it for this application.
    """
    student = db.get(User, application.student_id)
    profile = _student_profile(db, application.student_id)
    offer = db.scalar(select(Offer).where(Offer.application_id == application.id))
    has_active_offer = offer is not None and offer.status in (
        OfferStatus.extended,
        OfferStatus.accepted,
    )
    return RecruiterCandidateOut(
        application_id=application.id,
        drive_id=drive.id,
        drive_role=drive.role_title,
        status=application.status,
        full_name=student.full_name if student else "(unknown)",
        cgpa=profile["cgpa"],
        attendance=profile["attendance"],
        verified_skills=profile["verified_skills"],
        verified_projects=profile["verified_projects"],
        verified_internships=profile["verified_internships"],
        contact_revealed=application.contact_revealed,
        email=(
            student.email
            if (application.contact_revealed and student is not None)
            else None
        ),
        recruiter_decision=application.recruiter_decision,
        recruiter_decision_note=application.recruiter_decision_note,
        has_active_offer=has_active_offer,
    )


@router.get("/me/drives", response_model=list[RecruiterDriveOut])
def my_drives(
    current_user: User = Depends(recruiter_only),
    db: Session = Depends(get_db),
) -> list[RecruiterDriveOut]:
    """List the drives the TPO has linked to the recruiter's company."""
    _link, recruiter = _recruiter_for_user(db, current_user)
    drives = list(
        db.scalars(
            select(Drive)
            .where(Drive.recruiter_id == recruiter.id)
            .order_by(Drive.created_at.desc())
        )
    )
    out: list[RecruiterDriveOut] = []
    for drive in drives:
        counts = {
            s: (
                db.scalar(
                    select(func.count(Application.id)).where(
                        Application.drive_id == drive.id,
                        Application.status == s,
                    )
                )
                or 0
            )
            for s in _VISIBLE_TO_RECRUITER
        }
        out.append(
            RecruiterDriveOut(
                id=drive.id,
                company_name=drive.company_name,
                role_title=drive.role_title,
                location=drive.location,
                package_lpa=drive.package_lpa,
                is_open=drive.is_open,
                deadline=drive.deadline,
                shortlisted_count=counts[ApplicationStatus.shortlisted],
                selected_count=counts[ApplicationStatus.selected],
            )
        )
    return out


@router.get("/me/candidates", response_model=list[RecruiterCandidateOut])
def my_candidates(
    drive_id: int | None = None,
    status_filter: ApplicationStatus | None = None,
    current_user: User = Depends(recruiter_only),
    db: Session = Depends(get_db),
) -> list[RecruiterCandidateOut]:
    """List shortlisted/selected candidates across the recruiter's drives.

    Only candidates the TPO has shortlisted or selected are visible, and only
    on drives linked to this recruiter's company. Contact stays masked until
    the TPO reveals it per candidate.
    """
    _link, recruiter = _recruiter_for_user(db, current_user)

    # Restrict strictly to this company's linked drives.
    drive_stmt = select(Drive).where(Drive.recruiter_id == recruiter.id)
    if drive_id is not None:
        drive_stmt = drive_stmt.where(Drive.id == drive_id)
    drives = {d.id: d for d in db.scalars(drive_stmt)}
    if not drives:
        return []

    if status_filter is not None and status_filter not in _VISIBLE_TO_RECRUITER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recruiters can only view shortlisted or selected candidates.",
        )
    visible = (
        (status_filter,) if status_filter is not None else _VISIBLE_TO_RECRUITER
    )

    applications = list(
        db.scalars(
            select(Application)
            .where(
                Application.drive_id.in_(list(drives.keys())),
                Application.status.in_(visible),
            )
            .order_by(Application.created_at.desc())
        )
    )

    # Selected first, then shortlisted; then by CGPA desc.
    rank = {ApplicationStatus.selected: 0, ApplicationStatus.shortlisted: 1}
    cards = [
        _candidate_out(db, application, drives[application.drive_id])
        for application in applications
    ]
    cards.sort(key=lambda c: (rank.get(c.status, 9), -c.cgpa))
    return cards


# --- TPO: link drives & reveal contact (Step 27.2) -------------------------
@router.patch("/drives/{drive_id}/recruiter", response_model=DriveOut)
def link_drive_to_recruiter(
    drive_id: int,
    payload: DriveRecruiterLink,
    current_user: User = Depends(staff_only),
    db: Session = Depends(get_db),
) -> Drive:
    """Link (or unlink) a drive to a recruiting company (TPO/admin).

    Pass `recruiter_id: null` to unlink. Once linked, the company's HR can see
    the drive's shortlisted/selected candidates.
    """
    drive = db.get(Drive, drive_id)
    if drive is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Drive not found"
        )
    if payload.recruiter_id is not None:
        recruiter = db.get(Recruiter, payload.recruiter_id)
        if recruiter is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Company not found"
            )
        drive.recruiter_id = recruiter.id
        summary = f"Linked drive '{drive.role_title}' to {recruiter.company_name}"
    else:
        drive.recruiter_id = None
        summary = f"Unlinked drive '{drive.role_title}' from its company"
    record_audit(
        db,
        current_user,
        "recruiter.drive_link",
        summary,
        target_type="drive",
        target_id=drive.id,
    )
    db.commit()
    db.refresh(drive)
    return drive


@router.patch(
    "/applications/{application_id}/contact", response_model=ApplicationOut
)
def set_contact_visibility(
    application_id: int,
    payload: ContactRevealUpdate,
    current_user: User = Depends(staff_only),
    db: Session = Depends(get_db),
) -> Application:
    """Reveal or hide a candidate's contact details to the recruiter (TPO)."""
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Application not found"
        )
    application.contact_revealed = payload.revealed
    verb = "Revealed" if payload.revealed else "Hid"
    record_audit(
        db,
        current_user,
        "recruiter.contact_reveal",
        f"{verb} contact for application {application.id}",
        target_type="application",
        target_id=application.id,
    )
    db.commit()
    db.refresh(application)
    return application


# --- Decisions & offers (Step 27.3) ----------------------------------------
def _offer_out(db: Session, offer: Offer) -> OfferOut:
    """Build an enriched offer card (adds drive/company/student context)."""
    drive = db.get(Drive, offer.drive_id)
    company = db.get(Recruiter, offer.recruiter_id)
    student = db.get(User, offer.student_id)
    return OfferOut(
        id=offer.id,
        application_id=offer.application_id,
        drive_id=offer.drive_id,
        drive_role=drive.role_title if drive else "(unknown)",
        company_name=company.company_name if company else "(unknown)",
        student_id=offer.student_id,
        student_name=student.full_name if student else "(unknown)",
        role_title=offer.role_title,
        package_lpa=offer.package_lpa,
        location=offer.location,
        joining_date=offer.joining_date,
        expires_on=offer.expires_on,
        status=offer.status,
        note=offer.note,
        student_response_note=offer.student_response_note,
        created_at=offer.created_at,
        responded_at=offer.responded_at,
    )


def _recruiter_application(
    db: Session, recruiter: Recruiter, application_id: int
) -> tuple[Application, Drive]:
    """Resolve an application the recruiter is allowed to act on.

    Enforces: the application exists, sits on a drive linked to THIS company,
    and is currently visible to recruiters (shortlisted/selected). Anything
    else is a 403/404 so a company can never poke at other drives' candidates.
    """
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found"
        )
    drive = db.get(Drive, application.drive_id)
    if drive is None or drive.recruiter_id != recruiter.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This candidate is not on one of your drives.",
        )
    if application.status not in _VISIBLE_TO_RECRUITER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This candidate is not visible to your company yet.",
        )
    return application, drive


@router.patch(
    "/me/candidates/{application_id}/decision",
    response_model=RecruiterCandidateOut,
)
def set_candidate_decision(
    application_id: int,
    payload: RecruiterDecisionUpdate,
    current_user: User = Depends(recruiter_only),
    db: Session = Depends(get_db),
) -> RecruiterCandidateOut:
    """Recruiter records a non-binding call on a visible candidate (27.3).

    This is the company's signal to the TPO (interested / on_hold / rejected);
    it never changes the official application status, which the TPO owns.
    """
    if payload.decision == RecruiterDecision.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Choose interested, on_hold or rejected (not pending).",
        )
    _link, recruiter = _recruiter_for_user(db, current_user)
    application, drive = _recruiter_application(db, recruiter, application_id)
    application.recruiter_decision = payload.decision
    application.recruiter_decision_note = payload.note
    application.recruiter_decided_at = datetime.now(timezone.utc)
    record_audit(
        db,
        current_user,
        "recruiter.decision",
        (
            f"Recruiter marked application {application.id} as "
            f"{payload.decision.value} on '{drive.role_title}'"
        ),
        target_type="application",
        target_id=application.id,
    )
    db.commit()
    db.refresh(application)
    return _candidate_out(db, application, drive)


@router.post(
    "/me/offers",
    response_model=OfferOut,
    status_code=status.HTTP_201_CREATED,
)
def extend_offer(
    payload: OfferCreate,
    current_user: User = Depends(recruiter_only),
    db: Session = Depends(get_db),
) -> OfferOut:
    """Extend an offer to a visible candidate (recruiter, Step 27.3).

    Terms default to the drive's role/package/location when omitted. Only one
    live offer can exist per candidate; a previously withdrawn or declined
    offer's row is reused (re-extended).
    """
    _link, recruiter = _recruiter_for_user(db, current_user)
    application, drive = _recruiter_application(
        db, recruiter, payload.application_id
    )

    role_title = payload.role_title or drive.role_title
    package = (
        payload.package_lpa
        if payload.package_lpa is not None
        else drive.package_lpa
    )
    location = payload.location if payload.location is not None else drive.location

    existing = db.scalar(
        select(Offer).where(Offer.application_id == application.id)
    )
    if existing is not None and existing.status in (
        OfferStatus.extended,
        OfferStatus.accepted,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"An offer is already {existing.status.value} for this "
                "candidate."
            ),
        )

    if existing is not None:
        # Reuse the withdrawn/declined row (unique per application).
        offer = existing
        offer.recruiter_id = recruiter.id
        offer.tenant_id = drive.tenant_id
        offer.drive_id = drive.id
        offer.student_id = application.student_id
        offer.role_title = role_title
        offer.package_lpa = package
        offer.location = location
        offer.joining_date = payload.joining_date
        offer.expires_on = payload.expires_on
        offer.note = payload.note
        offer.status = OfferStatus.extended
        offer.created_by_id = current_user.id
        offer.student_response_note = None
        offer.responded_at = None
    else:
        offer = Offer(
            application_id=application.id,
            recruiter_id=recruiter.id,
            tenant_id=drive.tenant_id,
            drive_id=drive.id,
            student_id=application.student_id,
            role_title=role_title,
            package_lpa=package,
            location=location,
            joining_date=payload.joining_date,
            expires_on=payload.expires_on,
            note=payload.note,
            status=OfferStatus.extended,
            created_by_id=current_user.id,
        )
        db.add(offer)

    record_audit(
        db,
        current_user,
        "recruiter.offer_extend",
        f"Extended offer for application {application.id} ('{role_title}')",
        target_type="application",
        target_id=application.id,
    )
    db.commit()
    db.refresh(offer)
    return _offer_out(db, offer)


@router.get("/me/offers", response_model=list[OfferOut])
def list_my_offers(
    current_user: User = Depends(recruiter_only),
    db: Session = Depends(get_db),
) -> list[OfferOut]:
    """List all offers this recruiter's company has made (newest first)."""
    _link, recruiter = _recruiter_for_user(db, current_user)
    offers = db.scalars(
        select(Offer)
        .where(Offer.recruiter_id == recruiter.id)
        .order_by(Offer.created_at.desc())
    )
    return [_offer_out(db, offer) for offer in offers]


@router.patch("/me/offers/{offer_id}/withdraw", response_model=OfferOut)
def withdraw_offer(
    offer_id: int,
    current_user: User = Depends(recruiter_only),
    db: Session = Depends(get_db),
) -> OfferOut:
    """Withdraw a still-pending offer (recruiter). Accepted ones are locked."""
    _link, recruiter = _recruiter_for_user(db, current_user)
    offer = db.get(Offer, offer_id)
    if offer is None or offer.recruiter_id != recruiter.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found"
        )
    if offer.status != OfferStatus.extended:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Only an extended offer can be withdrawn; this one is "
                f"{offer.status.value}."
            ),
        )
    offer.status = OfferStatus.withdrawn
    record_audit(
        db,
        current_user,
        "recruiter.offer_withdraw",
        f"Withdrew offer {offer.id} for application {offer.application_id}",
        target_type="application",
        target_id=offer.application_id,
    )
    db.commit()
    db.refresh(offer)
    return _offer_out(db, offer)


# --- Student: view & respond to offers (Step 27.3) -------------------------
@router.get("/offers/mine", response_model=list[OfferOut])
def my_student_offers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[OfferOut]:
    """List the offers extended to the logged-in student (newest first)."""
    offers = db.scalars(
        select(Offer)
        .where(
            Offer.tenant_id == current_user.tenant_id,
            Offer.student_id == current_user.id,
        )
        .order_by(Offer.created_at.desc())
    )
    return [_offer_out(db, offer) for offer in offers]


@router.patch("/offers/{offer_id}/respond", response_model=OfferOut)
def respond_to_offer(
    offer_id: int,
    payload: OfferRespond,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OfferOut:
    """Student accepts or declines an offer extended to them (Step 27.3).

    Only the recipient can respond, and only while the offer is still
    `extended`. The official placement status stays with the TPO - accepting
    an offer records the student's intent; the TPO finalises `selected`.
    """
    offer = db.get(Offer, offer_id)
    if offer is None or offer.student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found"
        )
    if offer.status != OfferStatus.extended:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"This offer is {offer.status.value} and can no longer be "
                "changed."
            ),
        )
    offer.status = (
        OfferStatus.accepted if payload.accept else OfferStatus.declined
    )
    offer.student_response_note = payload.note
    offer.responded_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(offer)
    return _offer_out(db, offer)


# --- TPO/admin: oversight of all offers (Step 27.3) ------------------------
@router.get(
    "/offers",
    response_model=list[OfferOut],
    dependencies=[Depends(staff_only)],
)
def list_all_offers(db: Session = Depends(get_db)) -> list[OfferOut]:
    """List every offer across all companies (TPO/admin oversight)."""
    offers = db.scalars(select(Offer).order_by(Offer.created_at.desc()))
    return [_offer_out(db, offer) for offer in offers]
