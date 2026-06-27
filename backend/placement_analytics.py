"""Placement analytics routes - TPO/admin dashboard over drives + applications.

Read-only aggregation on top of the placement core (drives, applications,
shortlisting). Surfaces the recruitment funnel, placement rate, per-drive
performance, and a company leaderboard so the TPO can see outcomes at a glance.

No new tables - everything is computed at read time from existing data.

Mounted under the `/placement/analytics` prefix by `main.py` (a dedicated
prefix avoids colliding with `/drives/{drive_id}`).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from db import get_db
from models import Application, ApplicationStatus, Drive, User, UserRole
from schemas import (
    CompanyStatOut,
    DrivePerformanceOut,
    PlacementAnalyticsOut,
    PlacementFunnelOut,
)
from security import require_roles

router = APIRouter(prefix="/placement/analytics", tags=["placement-analytics"])

# Placement outcomes are the TPO's domain; admins may also view them.
staff_only = require_roles(UserRole.tpo, UserRole.admin)


def _rate(part: int, whole: int) -> float | None:
    """Percentage part/whole, or None when there is nothing to divide by."""
    if whole <= 0:
        return None
    return round(part / whole * 100, 1)


def _avg(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


def _count(items: list[Application], st: ApplicationStatus) -> int:
    return sum(1 for a in items if a.status == st)


@router.get("/overview", response_model=PlacementAnalyticsOut)
def placement_overview(
    db: Session = Depends(get_db),
    _staff: User = Depends(staff_only),
) -> PlacementAnalyticsOut:
    """Whole-program placement analytics: funnel, rate, per-drive + companies."""
    drives = list(db.scalars(select(Drive)))
    apps = list(db.scalars(select(Application)))

    total_active_students = (
        db.scalar(
            select(func.count(User.id)).where(
                User.role == UserRole.student, User.is_active.is_(True)
            )
        )
        or 0
    )

    # Group applications by drive id for per-drive aggregation.
    by_drive: dict[int, list[Application]] = {}
    for app in apps:
        by_drive.setdefault(app.drive_id, []).append(app)

    # Funnel = current status distribution across every application.
    funnel = PlacementFunnelOut(
        applied=_count(apps, ApplicationStatus.applied),
        shortlisted=_count(apps, ApplicationStatus.shortlisted),
        selected=_count(apps, ApplicationStatus.selected),
        rejected=_count(apps, ApplicationStatus.rejected),
    )

    unique_applicants = len({a.student_id for a in apps})
    placed_students = len(
        {a.student_id for a in apps if a.status == ApplicationStatus.selected}
    )

    # Per-drive performance.
    drive_rows: list[DrivePerformanceOut] = []
    for drive in drives:
        items = by_drive.get(drive.id, [])
        applicants = len(items)
        selected = _count(items, ApplicationStatus.selected)
        drive_rows.append(
            DrivePerformanceOut(
                drive_id=drive.id,
                company_name=drive.company_name,
                role_title=drive.role_title,
                package_lpa=drive.package_lpa,
                is_open=drive.is_open,
                applicants=applicants,
                shortlisted=_count(items, ApplicationStatus.shortlisted),
                selected=selected,
                rejected=_count(items, ApplicationStatus.rejected),
                selection_rate=_rate(selected, applicants),
            )
        )
    # Most-active drives first (by applicants, then selected).
    drive_rows.sort(key=lambda d: (d.applicants, d.selected), reverse=True)

    # Company leaderboard (a company may run several drives).
    companies: dict[str, dict] = {}
    for row in drive_rows:
        c = companies.setdefault(
            row.company_name,
            {"drives": 0, "applicants": 0, "selected": 0, "packages": []},
        )
        c["drives"] += 1
        c["applicants"] += row.applicants
        c["selected"] += row.selected
        if row.package_lpa is not None:
            c["packages"].append(row.package_lpa)
    company_rows = [
        CompanyStatOut(
            company_name=name,
            drives=info["drives"],
            applicants=info["applicants"],
            selected=info["selected"],
            avg_package=_avg(info["packages"]),
        )
        for name, info in companies.items()
    ]
    company_rows.sort(key=lambda c: (c.selected, c.applicants), reverse=True)

    # Package stats over drives that advertise a package.
    packages = [d.package_lpa for d in drives if d.package_lpa is not None]
    highest = max(packages) if packages else None
    highest_company = None
    if highest is not None:
        highest_company = next(
            (d.company_name for d in drives if d.package_lpa == highest), None
        )

    return PlacementAnalyticsOut(
        total_drives=len(drives),
        open_drives=sum(1 for d in drives if d.is_open),
        closed_drives=sum(1 for d in drives if not d.is_open),
        total_applications=len(apps),
        unique_applicants=unique_applicants,
        placed_students=placed_students,
        total_active_students=total_active_students,
        placement_rate=_rate(placed_students, total_active_students),
        applicant_conversion=_rate(placed_students, unique_applicants),
        avg_package=_avg(packages),
        highest_package=highest,
        highest_package_company=highest_company,
        funnel=funnel,
        drives=drive_rows,
        companies=company_rows,
    )
