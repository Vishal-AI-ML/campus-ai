"""Placement routes - drives + the verified-data eligibility engine.

This is where the 'verified data moat' turns into placement value: the TPO
posts a drive with criteria, and the engine decides which students qualify
based ONLY on their VERIFIED profile:
  * CGPA (credit-weighted, from results)
  * attendance % ((present + late) / total)
  * count of VERIFIED skills matching the drive's required skills
  * count of VERIFIED project contributions

Every verdict is explainable (per-criterion pass/fail reasons), so the TPO can
trust and defend it.

Role model:
  * TPO posts drives, opens/closes them, and runs eligibility.
  * Any logged-in student can browse open drives and check their own
    eligibility breakdown.

(Applications + shortlisting are the next step; this step is drives +
eligibility.)

Mounted under the `/drives` prefix by `main.py`.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from db import get_db
from models import (
    Application,
    ApplicationStatus,
    AttendanceRecord,
    AttendanceStatus,
    Drive,
    ProjectMember,
    Result,
    Skill,
    SkillStatus,
    Subject,
    User,
    UserRole,
)
from schemas import (
    ApplicantOut,
    ApplicationOut,
    ApplicationStatusUpdate,
    DriveCreate,
    DriveOut,
    DriveStatusUpdate,
    MyApplicationOut,
    MyEligibilityOut,
    StudentEligibilityOut,
)
from security import get_current_user, require_roles

router = APIRouter(prefix="/drives", tags=["placement"])

# Drives are the TPO's domain; admins may also list them.
tpo_only = require_roles(UserRole.tpo)
staff_only = require_roles(UserRole.tpo, UserRole.admin)


# --- Eligibility engine (pure-ish helpers) ---------------------------------
def _parse_required_skills(raw: str | None) -> list[str]:
    """Split the comma-separated required-skills string into clean names."""
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _student_profile(db: Session, student_id: int) -> dict:
    """Compute one student's VERIFIED profile metrics used for eligibility."""
    # CGPA - credit-weighted average of grade points.
    gp_rows = db.execute(
        select(Result.grade_point, Subject.credits).join(
            Subject, Result.subject_id == Subject.id
        ).where(Result.student_id == student_id)
    ).all()
    total_credits = sum(credits for _, credits in gp_rows)
    cgpa = (
        round(sum(gp * credits for gp, credits in gp_rows) / total_credits, 2)
        if total_credits
        else 0.0
    )

    # Attendance % - (present + late) / total.
    statuses = list(
        db.scalars(
            select(AttendanceRecord.status).where(
                AttendanceRecord.student_id == student_id
            )
        )
    )
    total = len(statuses)
    attended = sum(
        1 for s in statuses if s in (AttendanceStatus.present, AttendanceStatus.late)
    )
    attendance = round(attended / total * 100, 1) if total else 0.0

    # Verified skills (names) and verified project-contribution count.
    verified_skills = list(
        db.scalars(
            select(Skill.name).where(
                Skill.student_id == student_id, Skill.status == SkillStatus.verified
            )
        )
    )
    verified_projects = (
        db.scalar(
            select(func.count(ProjectMember.id)).where(
                ProjectMember.student_id == student_id,
                ProjectMember.status == SkillStatus.verified,
            )
        )
        or 0
    )

    return {
        "cgpa": cgpa,
        "attendance": attendance,
        "verified_skills": verified_skills,
        "verified_projects": verified_projects,
    }


def _evaluate(profile: dict, drive: Drive) -> tuple[bool, list[dict]]:
    """Check a profile against a drive's criteria. Returns (eligible, reasons)."""
    required = _parse_required_skills(drive.required_skills)
    verified_lower = {name.lower() for name in profile["verified_skills"]}
    missing = [name for name in required if name.lower() not in verified_lower]

    checks = [
        (
            "CGPA",
            profile["cgpa"] >= drive.min_cgpa,
            f"{profile['cgpa']} (need >= {drive.min_cgpa})",
        ),
        (
            "Attendance",
            profile["attendance"] >= drive.min_attendance,
            f"{profile['attendance']}% (need >= {drive.min_attendance}%)",
        ),
        (
            "Verified projects",
            profile["verified_projects"] >= drive.min_verified_projects,
            f"{profile['verified_projects']} (need >= {drive.min_verified_projects})",
        ),
        (
            "Required skills",
            len(missing) == 0,
            "all present" if not missing else f"missing: {', '.join(missing)}",
        ),
    ]
    reasons = [
        {"criterion": c, "passed": passed, "detail": detail}
        for c, passed, detail in checks
    ]
    eligible = all(passed for _, passed, _ in checks)
    return eligible, reasons


def _require_drive(db: Session, drive_id: int) -> Drive:
    drive = db.get(Drive, drive_id)
    if drive is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Drive not found"
        )
    return drive


# --- TPO: manage drives ----------------------------------------------------
@router.post("", response_model=DriveOut, status_code=status.HTTP_201_CREATED)
def create_drive(
    payload: DriveCreate,
    db: Session = Depends(get_db),
    tpo: User = Depends(tpo_only),
) -> Drive:
    """Post a new placement drive with its eligibility criteria."""
    drive = Drive(
        company_name=payload.company_name,
        role_title=payload.role_title,
        description=payload.description,
        location=payload.location,
        package_lpa=payload.package_lpa,
        min_cgpa=payload.min_cgpa,
        min_attendance=payload.min_attendance,
        min_verified_projects=payload.min_verified_projects,
        required_skills=payload.required_skills,
        deadline=payload.deadline,
        created_by_id=tpo.id,
    )
    db.add(drive)
    db.commit()
    db.refresh(drive)
    return drive


@router.get("", response_model=list[DriveOut], dependencies=[Depends(staff_only)])
def list_drives(
    open_only: bool = False,
    db: Session = Depends(get_db),
) -> list[Drive]:
    """List all drives (TPO/admin). Optionally only the open ones."""
    stmt = select(Drive)
    if open_only:
        stmt = stmt.where(Drive.is_open.is_(True))
    return list(db.scalars(stmt.order_by(Drive.created_at.desc())))


@router.get("/open", response_model=list[DriveOut])
def open_drives(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[Drive]:
    """Browse currently open drives (any logged-in user)."""
    return list(
        db.scalars(
            select(Drive).where(Drive.is_open.is_(True)).order_by(
                Drive.created_at.desc()
            )
        )
    )


@router.get("/{drive_id}", response_model=DriveOut)
def get_drive(
    drive_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> Drive:
    """Fetch a single drive by id."""
    return _require_drive(db, drive_id)


@router.patch("/{drive_id}/status", response_model=DriveOut)
def set_drive_status(
    drive_id: int,
    payload: DriveStatusUpdate,
    db: Session = Depends(get_db),
    _tpo: User = Depends(tpo_only),
) -> Drive:
    """Open or close a drive."""
    drive = _require_drive(db, drive_id)
    drive.is_open = payload.is_open
    db.commit()
    db.refresh(drive)
    return drive


# --- Eligibility ------------------------------------------------------------
@router.get(
    "/{drive_id}/eligibility",
    response_model=list[StudentEligibilityOut],
    dependencies=[Depends(tpo_only)],
)
def drive_eligibility(
    drive_id: int,
    eligible_only: bool = False,
    db: Session = Depends(get_db),
) -> list[StudentEligibilityOut]:
    """Run the eligibility engine across all active students for this drive.

    Returns each student's verdict with explainable per-criterion reasons,
    eligible students first (then by CGPA).
    """
    drive = _require_drive(db, drive_id)
    students = list(
        db.scalars(
            select(User).where(
                User.role == UserRole.student, User.is_active.is_(True)
            )
        )
    )
    results: list[StudentEligibilityOut] = []
    for student in students:
        profile = _student_profile(db, student.id)
        eligible, reasons = _evaluate(profile, drive)
        if eligible_only and not eligible:
            continue
        results.append(
            StudentEligibilityOut(
                student_id=student.id,
                full_name=student.full_name,
                eligible=eligible,
                cgpa=profile["cgpa"],
                attendance=profile["attendance"],
                verified_skills=len(profile["verified_skills"]),
                verified_projects=profile["verified_projects"],
                reasons=reasons,
            )
        )
    results.sort(key=lambda r: (not r.eligible, -r.cgpa))
    return results


@router.get("/{drive_id}/my-eligibility", response_model=MyEligibilityOut)
def my_eligibility(
    drive_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MyEligibilityOut:
    """Check YOUR own eligibility for a drive, with per-criterion reasons."""
    drive = _require_drive(db, drive_id)
    profile = _student_profile(db, current_user.id)
    eligible, reasons = _evaluate(profile, drive)
    return MyEligibilityOut(
        drive_id=drive_id,
        eligible=eligible,
        cgpa=profile["cgpa"],
        attendance=profile["attendance"],
        verified_skills=len(profile["verified_skills"]),
        verified_projects=profile["verified_projects"],
        reasons=reasons,
    )


# --- Applications + shortlisting -------------------------------------------
@router.post(
    "/{drive_id}/apply",
    response_model=ApplicationOut,
    status_code=status.HTTP_201_CREATED,
)
def apply_to_drive(
    drive_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Application:
    """Apply to a drive. Only open drives and eligible students are allowed.

    Eligibility is re-checked here against the student's VERIFIED data, so an
    application can only exist if the moat criteria are genuinely met.
    """
    drive = _require_drive(db, drive_id)
    if not drive.is_open:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This drive is closed for applications.",
        )

    existing = db.scalar(
        select(Application).where(
            Application.drive_id == drive_id,
            Application.student_id == current_user.id,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already applied to this drive.",
        )

    profile = _student_profile(db, current_user.id)
    eligible, reasons = _evaluate(profile, drive)
    if not eligible:
        unmet = [r["detail"] for r in reasons if not r["passed"]]
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not eligible for this drive: " + "; ".join(unmet),
        )

    application = Application(drive_id=drive_id, student_id=current_user.id)
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@router.get("/me/applications", response_model=list[MyApplicationOut])
def my_applications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Application]:
    """List the logged-in student's own applications (with drive context)."""
    return list(
        db.scalars(
            select(Application)
            .where(Application.student_id == current_user.id)
            .order_by(Application.created_at.desc())
        )
    )


@router.get(
    "/{drive_id}/applications",
    response_model=list[ApplicantOut],
    dependencies=[Depends(tpo_only)],
)
def drive_applications(
    drive_id: int,
    status_filter: ApplicationStatus | None = None,
    db: Session = Depends(get_db),
) -> list[ApplicantOut]:
    """List applicants on a drive (TPO), each with a verified-data snapshot.

    Selected/shortlisted candidates are surfaced first, then by CGPA.
    """
    drive = _require_drive(db, drive_id)
    stmt = select(Application).where(Application.drive_id == drive_id)
    if status_filter is not None:
        stmt = stmt.where(Application.status == status_filter)
    applications = list(db.scalars(stmt))

    # Rank: selected, shortlisted, applied, rejected - then by CGPA desc.
    rank = {
        ApplicationStatus.selected: 0,
        ApplicationStatus.shortlisted: 1,
        ApplicationStatus.applied: 2,
        ApplicationStatus.rejected: 3,
    }
    out: list[ApplicantOut] = []
    for application in applications:
        student = db.get(User, application.student_id)
        if student is None:
            continue
        profile = _student_profile(db, student.id)
        eligible, _reasons = _evaluate(profile, drive)
        out.append(
            ApplicantOut(
                application_id=application.id,
                student_id=student.id,
                full_name=student.full_name,
                status=application.status,
                eligible=eligible,
                cgpa=profile["cgpa"],
                attendance=profile["attendance"],
                verified_skills=len(profile["verified_skills"]),
                verified_projects=profile["verified_projects"],
                note=application.note,
            )
        )
    out.sort(key=lambda a: (rank.get(a.status, 9), -a.cgpa))
    return out


@router.patch(
    "/applications/{application_id}/status", response_model=ApplicationOut
)
def set_application_status(
    application_id: int,
    payload: ApplicationStatusUpdate,
    db: Session = Depends(get_db),
    tpo: User = Depends(tpo_only),
) -> Application:
    """TPO decision on an application: shortlist, select, or reject."""
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Application not found"
        )
    if payload.status == ApplicationStatus.applied:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot move an application back to 'applied'.",
        )
    application.status = payload.status
    application.note = payload.note
    application.decided_by_id = tpo.id
    application.decided_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(application)
    return application
