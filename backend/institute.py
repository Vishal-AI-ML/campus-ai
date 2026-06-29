"""Institute-wide dashboard - admin KPI snapshot across the whole platform.

A single READ-ONLY aggregation endpoint that rolls up the numbers an
administrator cares about into one payload:

  * People      - accounts by role, active vs disabled, section coverage
  * Structure   - departments / sections / subjects
  * Moat        - verified vs pending proof (skills, projects, ECA,
                  internships): the anti-fraud data moat at a glance
  * Academics   - average attendance %, CGPA coverage + mean (across sections)
  * Placement   - drives, applications, placed, rate, package stats
  * Engagement  - assignments, submissions, materials, doubts, leave queue
  * Risk        - at-risk band distribution, reusing the transparent model

No new tables, no migration - everything is computed at request time from
data the institute already trusts. Admin-only.

Mounted under the `/institute` prefix by `main.py`.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from analytics import _assess_section
from db import get_db
from models import (
    Announcement,
    Application,
    ApplicationStatus,
    Assignment,
    Department,
    Doubt,
    DoubtStatus,
    Drive,
    ExtraCurricular,
    Internship,
    LeaveRequest,
    LeaveStatus,
    Material,
    ProjectMember,
    Recruiter,
    Section,
    Skill,
    SkillStatus,
    Subject,
    User,
    UserRole,
)
from schemas import (
    InstituteAcademicsKpi,
    InstituteDashboardOut,
    InstituteEngagementKpi,
    InstituteMoatKpi,
    InstitutePlacementKpi,
    InstituteRiskKpi,
    InstituteStructureKpi,
    InstituteUsersKpi,
)
from security import require_roles

router = APIRouter(prefix="/institute", tags=["institute"])

# Institute-wide oversight is the administrator's job.
admin_only = require_roles(UserRole.admin)


def _n(db: Session, col, *where) -> int:
    """COUNT over `col` with optional filters (None-safe -> 0)."""
    stmt = select(func.count(col))
    if where:
        stmt = stmt.where(*where)
    return db.scalar(stmt) or 0


def _avg(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


def _rate(part: int, whole: int) -> float | None:
    """Percentage part/whole, or None when there is nothing to divide by."""
    if whole <= 0:
        return None
    return round(part / whole * 100, 1)


@router.get("/dashboard", response_model=InstituteDashboardOut)
def institute_dashboard(
    db: Session = Depends(get_db),
    _admin: User = Depends(admin_only),
) -> InstituteDashboardOut:
    """Whole-institute KPI snapshot for the admin dashboard."""
    # --- People -----------------------------------------------------------
    role_counts = dict(
        db.execute(
            select(User.role, func.count(User.id)).group_by(User.role)
        ).all()
    )
    users = InstituteUsersKpi(
        total=_n(db, User.id),
        active=_n(db, User.id, User.is_active.is_(True)),
        inactive=_n(db, User.id, User.is_active.is_(False)),
        students=role_counts.get(UserRole.student, 0),
        teachers=role_counts.get(UserRole.teacher, 0),
        tpos=role_counts.get(UserRole.tpo, 0),
        admins=role_counts.get(UserRole.admin, 0),
        recruiters=role_counts.get(UserRole.recruiter, 0),
        students_with_section=_n(
            db,
            User.id,
            User.role == UserRole.student,
            User.section_id.is_not(None),
        ),
    )

    # --- Structure --------------------------------------------------------
    structure = InstituteStructureKpi(
        departments=_n(db, Department.id),
        sections=_n(db, Section.id),
        subjects=_n(db, Subject.id),
    )

    # --- Verified-data moat ----------------------------------------------
    moat = InstituteMoatKpi(
        skills_verified=_n(db, Skill.id, Skill.status == SkillStatus.verified),
        skills_pending=_n(db, Skill.id, Skill.status == SkillStatus.pending),
        projects_verified=_n(
            db, ProjectMember.id, ProjectMember.status == SkillStatus.verified
        ),
        projects_pending=_n(
            db, ProjectMember.id, ProjectMember.status == SkillStatus.pending
        ),
        eca_verified=_n(
            db, ExtraCurricular.id, ExtraCurricular.status == SkillStatus.verified
        ),
        eca_pending=_n(
            db, ExtraCurricular.id, ExtraCurricular.status == SkillStatus.pending
        ),
        internships_verified=_n(
            db, Internship.id, Internship.status == SkillStatus.verified
        ),
        internships_pending=_n(
            db, Internship.id, Internship.status == SkillStatus.pending
        ),
    )

    # --- Academics + Risk (one pass over every section) -------------------
    # Reuse the transparent, explainable risk model from analytics so the
    # institute view stays consistent with what teachers see per-section.
    bands = {"high": 0, "medium": 0, "low": 0}
    att_vals: list[float] = []
    cgpa_vals: list[float] = []
    assessed = 0
    for section in db.scalars(select(Section)):
        for a in _assess_section(db, section):
            assessed += 1
            bands[a.band] = bands.get(a.band, 0) + 1
            if a.attendance_pct is not None:
                att_vals.append(a.attendance_pct)
            if a.cgpa is not None:
                cgpa_vals.append(a.cgpa)

    academics = InstituteAcademicsKpi(
        avg_attendance_pct=_avg(att_vals),
        students_with_results=len(cgpa_vals),
        avg_cgpa=_avg(cgpa_vals),
    )
    risk = InstituteRiskKpi(
        assessed_students=assessed,
        high=bands["high"],
        medium=bands["medium"],
        low=bands["low"],
    )

    # --- Placement --------------------------------------------------------
    drives = list(db.scalars(select(Drive)))
    apps = list(db.scalars(select(Application)))
    placed_students = len(
        {a.student_id for a in apps if a.status == ApplicationStatus.selected}
    )
    active_students = _n(
        db, User.id, User.role == UserRole.student, User.is_active.is_(True)
    )
    packages = [d.package_lpa for d in drives if d.package_lpa is not None]
    placement = InstitutePlacementKpi(
        total_drives=len(drives),
        open_drives=sum(1 for d in drives if d.is_open),
        total_applications=len(apps),
        placed_students=placed_students,
        placement_rate=_rate(placed_students, active_students),
        avg_package=_avg(packages),
        highest_package=max(packages) if packages else None,
        recruiter_companies=_n(db, Recruiter.id),
    )

    # --- Engagement -------------------------------------------------------
    engagement = InstituteEngagementKpi(
        assignments=_n(db, Assignment.id),
        submissions=_n(db, Submission.id),
        materials=_n(db, Material.id),
        doubts_open=_n(db, Doubt.id, Doubt.status == DoubtStatus.open),
        doubts_resolved=_n(db, Doubt.id, Doubt.status == DoubtStatus.resolved),
        announcements=_n(db, Announcement.id),
        leave_pending=_n(
            db, LeaveRequest.id, LeaveRequest.status == LeaveStatus.pending
        ),
    )

    return InstituteDashboardOut(
        generated_at=datetime.now(timezone.utc),
        users=users,
        structure=structure,
        moat=moat,
        academics=academics,
        placement=placement,
        engagement=engagement,
        risk=risk,
    )
