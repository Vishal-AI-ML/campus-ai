"""Analytics + At-risk routes (teacher / staff dashboard).

Two things, both READ-ONLY (no new tables, no migration):

  * Class analytics  -> GET /analytics/section/{id}
      Aggregate health of a section: roster size, average (condonation-aware)
      attendance %, average CGPA, assignment submission rate, and a risk-band
      distribution.

  * At-risk students -> GET /analytics/section/{id}/at-risk
      Per-student risk score (0-100, higher = more at risk) with a fully
      EXPLAINABLE factor breakdown + plain-English reasons. No black-box ML:
      a transparent weighted model over data the institute already trusts
      (attendance, grades, submissions) so teachers can act on it with
      confidence (human-in-the-loop, moat-consistent). The AI worker can layer
      narrative advice on top later.

A student can also see their own assessment -> GET /analytics/me.

Mounted under the `/analytics` prefix by `main.py`.
"""

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from attendance import _approved_ranges_for, _covering_request
from db import get_db
from models import (
    Assignment,
    AttendanceRecord,
    AttendanceStatus,
    LeaveRequest,
    Result,
    Section,
    Subject,
    Submission,
    User,
    UserRole,
)
from schemas import ClassAnalyticsOut, RiskFactorOut, StudentRiskOut
from security import get_current_user, require_roles

router = APIRouter(prefix="/analytics", tags=["analytics"])

staff_only = require_roles(UserRole.teacher, UserRole.tpo, UserRole.admin)

# --- Risk model knobs (transparent + tunable) -----------------------------
# Higher score = more at risk. Each factor is scored 0-100 then blended by
# weight; only factors that actually have data are counted (weights are
# renormalised over what's available).
WEIGHTS = {"attendance": 0.40, "academics": 0.35, "submission": 0.25}
# Bands on the blended 0-100 score.
HIGH_BAND = 60.0
MEDIUM_BAND = 35.0
# Reason thresholds (the point at which a factor is worth flagging).
ATTENDANCE_FLAG_PCT = 75.0
CGPA_FLAG = 6.0
SUBMISSION_FLAG_PCT = 60.0


def _band_for(score: float) -> str:
    if score >= HIGH_BAND:
        return "high"
    if score >= MEDIUM_BAND:
        return "medium"
    return "low"


def _attendance_pct(
    records: list[AttendanceRecord], ranges: list[LeaveRequest]
) -> float | None:
    """Condonation-aware attendance %: approved leave/OD absences are excused
    (dropped from the denominator), matching the attendance module."""
    total = len(records)
    if total == 0:
        return None
    excused = 0
    attended = 0
    for r in records:
        if r.status == AttendanceStatus.absent and _covering_request(
            ranges, r.date
        ):
            excused += 1
        elif r.status in (AttendanceStatus.present, AttendanceStatus.late):
            attended += 1
    effective = total - excused
    if effective <= 0:
        return None
    return round(attended / effective * 100, 1)


def _assess(
    student: User,
    records: list[AttendanceRecord],
    ranges: list[LeaveRequest],
    cgpa: float | None,
    total_assignments: int,
    submitted_count: int,
) -> StudentRiskOut:
    """Build one student's explainable risk assessment."""
    attendance_pct = _attendance_pct(records, ranges)
    submission_rate = (
        round(submitted_count / total_assignments * 100, 1)
        if total_assignments > 0
        else None
    )

    # Per-factor risk (0-100, higher = worse).
    att_risk = (
        None if attendance_pct is None else round(100 - attendance_pct, 1)
    )
    acad_risk = None if cgpa is None else round((10 - cgpa) * 10, 1)
    sub_risk = (
        None if submission_rate is None else round(100 - submission_rate, 1)
    )

    factors = [
        RiskFactorOut(
            key="attendance",
            label="Attendance",
            value=attendance_pct,
            risk=att_risk,
            weight=WEIGHTS["attendance"],
            available=att_risk is not None,
        ),
        RiskFactorOut(
            key="academics",
            label="Academics (CGPA)",
            value=cgpa,
            risk=acad_risk,
            weight=WEIGHTS["academics"],
            available=acad_risk is not None,
        ),
        RiskFactorOut(
            key="submission",
            label="Assignment submissions",
            value=submission_rate,
            risk=sub_risk,
            weight=WEIGHTS["submission"],
            available=sub_risk is not None,
        ),
    ]

    avail = [f for f in factors if f.available]
    total_w = sum(f.weight for f in avail)
    score = (
        round(sum((f.risk or 0) * f.weight for f in avail) / total_w, 1)
        if total_w > 0
        else 0.0
    )

    reasons: list[str] = []
    if attendance_pct is not None and attendance_pct < ATTENDANCE_FLAG_PCT:
        reasons.append(f"Low attendance: {attendance_pct}%")
    if cgpa is not None and cgpa < CGPA_FLAG:
        reasons.append(f"CGPA {cgpa} below {CGPA_FLAG}")
    if submission_rate is not None and submission_rate < SUBMISSION_FLAG_PCT:
        reasons.append(
            f"Submitted {submitted_count}/{total_assignments} assignments "
            f"({submission_rate}%)"
        )
    if not avail:
        reasons.append("Insufficient data to assess yet")

    return StudentRiskOut(
        student_id=student.id,
        student_name=student.full_name,
        risk_score=score,
        band="low" if not avail else _band_for(score),
        attendance_pct=attendance_pct,
        cgpa=cgpa,
        submission_rate=submission_rate,
        reasons=reasons,
        factors=factors,
    )


def _cgpa_map(db: Session, student_ids: list[int]) -> dict[int, float]:
    """Credit-weighted CGPA per student (only those with >=1 result)."""
    if not student_ids:
        return {}
    rows = db.execute(
        select(Result, Subject)
        .join(Subject, Result.subject_id == Subject.id)
        .where(Result.student_id.in_(student_ids))
    ).all()
    points: dict[int, float] = defaultdict(float)
    credits: dict[int, int] = defaultdict(int)
    for result, subject in rows:
        points[result.student_id] += result.grade_point * subject.credits
        credits[result.student_id] += subject.credits
    return {
        sid: round(points[sid] / credits[sid], 2)
        for sid in points
        if credits[sid]
    }


def _section_assignment_ids(db: Session, section_id: int) -> list[int]:
    return list(
        db.scalars(
            select(Assignment.id).where(Assignment.section_id == section_id)
        )
    )


def _assess_section(db: Session, section: Section) -> list[StudentRiskOut]:
    """Assess every student in a section (sorted most-at-risk first)."""
    students = list(
        db.scalars(
            select(User)
            .where(
                User.role == UserRole.student,
                User.section_id == section.id,
            )
            .order_by(User.full_name)
        )
    )
    if not students:
        return []
    ids = [s.id for s in students]

    records_by_student: dict[int, list[AttendanceRecord]] = defaultdict(list)
    for rec in db.scalars(
        select(AttendanceRecord).where(AttendanceRecord.student_id.in_(ids))
    ):
        records_by_student[rec.student_id].append(rec)
    ranges_by_student = _approved_ranges_for(db, ids)
    cgpa_by_student = _cgpa_map(db, ids)

    assignment_ids = _section_assignment_ids(db, section.id)
    total_assignments = len(assignment_ids)
    submitted_by_student: dict[int, int] = defaultdict(int)
    if assignment_ids:
        for sub in db.scalars(
            select(Submission).where(
                Submission.assignment_id.in_(assignment_ids),
                Submission.student_id.in_(ids),
            )
        ):
            submitted_by_student[sub.student_id] += 1

    assessments = [
        _assess(
            student=s,
            records=records_by_student.get(s.id, []),
            ranges=ranges_by_student.get(s.id, []),
            cgpa=cgpa_by_student.get(s.id),
            total_assignments=total_assignments,
            submitted_count=submitted_by_student.get(s.id, 0),
        )
        for s in students
    ]
    assessments.sort(key=lambda a: a.risk_score, reverse=True)
    return assessments


def _avg(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 1) if values else None


@router.get(
    "/section/{section_id}",
    response_model=ClassAnalyticsOut,
    dependencies=[Depends(staff_only)],
)
def section_analytics(
    section_id: int,
    db: Session = Depends(get_db),
) -> ClassAnalyticsOut:
    """Aggregate analytics + risk-band distribution for one section."""
    section = db.get(Section, section_id)
    if section is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Section not found"
        )
    assessments = _assess_section(db, section)
    att = [
        a.attendance_pct for a in assessments if a.attendance_pct is not None
    ]
    cg = [a.cgpa for a in assessments if a.cgpa is not None]
    sub = [
        a.submission_rate
        for a in assessments
        if a.submission_rate is not None
    ]
    high = sum(1 for a in assessments if a.band == "high")
    medium = sum(1 for a in assessments if a.band == "medium")
    low = len(assessments) - high - medium
    return ClassAnalyticsOut(
        section_id=section.id,
        section_name=section.name,
        student_count=len(assessments),
        avg_attendance_pct=_avg(att),
        avg_cgpa=(round(sum(cg) / len(cg), 2) if cg else None),
        results_coverage=len(cg),
        total_assignments=len(_section_assignment_ids(db, section.id)),
        avg_submission_rate=_avg(sub),
        risk_high=high,
        risk_medium=medium,
        risk_low=low,
        at_risk_count=high + medium,
    )


@router.get(
    "/section/{section_id}/at-risk",
    response_model=list[StudentRiskOut],
    dependencies=[Depends(staff_only)],
)
def section_at_risk(
    section_id: int,
    band: str | None = None,
    db: Session = Depends(get_db),
) -> list[StudentRiskOut]:
    """Per-student at-risk list for a section (most-at-risk first).

    Optional ?band=high|medium|low filter.
    """
    section = db.get(Section, section_id)
    if section is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Section not found"
        )
    assessments = _assess_section(db, section)
    if band in {"high", "medium", "low"}:
        assessments = [a for a in assessments if a.band == band]
    return assessments


@router.get("/me", response_model=StudentRiskOut)
def my_risk(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentRiskOut:
    """The logged-in student's own at-risk self-assessment (early warning)."""
    records = list(
        db.scalars(
            select(AttendanceRecord).where(
                AttendanceRecord.student_id == current_user.id
            )
        )
    )
    ranges = _approved_ranges_for(db, [current_user.id]).get(
        current_user.id, []
    )
    cgpa = _cgpa_map(db, [current_user.id]).get(current_user.id)

    total_assignments = 0
    submitted_count = 0
    if current_user.section_id is not None:
        assignment_ids = _section_assignment_ids(db, current_user.section_id)
        total_assignments = len(assignment_ids)
        if assignment_ids:
            submitted_count = len(
                list(
                    db.scalars(
                        select(Submission).where(
                            Submission.assignment_id.in_(assignment_ids),
                            Submission.student_id == current_user.id,
                        )
                    )
                )
            )

    return _assess(
        student=current_user,
        records=records,
        ranges=ranges,
        cgpa=cgpa,
        total_assignments=total_assignments,
        submitted_count=submitted_count,
    )
