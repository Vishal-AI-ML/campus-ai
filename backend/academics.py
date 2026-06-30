"""Academics routes: subjects (curriculum), results, grade points, SGPA/CGPA.

Role model (matches the product/prototype - 'Curriculum management: Teacher
access'):
  * TEACHER manages subjects (curriculum) and enters/updates student marks.
    The grade point (0-10) is derived from the percentage automatically.
  * STUDENT (any logged-in user) views subjects read-only, plus their own
    results and a CGPA + per-semester SGPA summary.

Mounted under the `/academics` prefix by `main.py`.
"""

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db import get_db
from models import Department, Result, Subject, User, UserRole
from schemas import (
    AcademicSummaryOut,
    ResultCreate,
    ResultOut,
    SemesterGPA,
    SubjectCreate,
    SubjectOut,
)
from security import get_current_user, require_roles

router = APIRouter(prefix="/academics", tags=["academics"])

# Curriculum + gradebook are a teacher's job.
teacher_only = require_roles(UserRole.teacher)


def grade_point_for(percentage: float) -> float:
    """Map a percentage to a 10-point grade point (standard slab scheme)."""
    if percentage >= 90:
        return 10.0
    if percentage >= 80:
        return 9.0
    if percentage >= 70:
        return 8.0
    if percentage >= 60:
        return 7.0
    if percentage >= 50:
        return 6.0
    if percentage >= 40:
        return 5.0
    return 0.0  # below 40% = fail = 0 grade points


# --- Subjects (curriculum) -------------------------------------------------
@router.post(
    "/subjects",
    response_model=SubjectOut,
    status_code=status.HTTP_201_CREATED,
)
def create_subject(
    payload: SubjectCreate,
    db: Session = Depends(get_db),
    _teacher: User = Depends(teacher_only),
) -> Subject:
    """Create a subject in a department. Code unique within the department."""
    department = db.get(Department, payload.department_id)
    # Tenant guard: a department from another institute is hidden as 404.
    if department is None or department.tenant_id != _teacher.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Department not found"
        )
    subject = Subject(
        tenant_id=department.tenant_id,
        name=payload.name,
        code=payload.code,
        credits=payload.credits,
        semester=payload.semester,
        department_id=payload.department_id,
    )
    db.add(subject)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A subject with this code already exists in this department",
        )
    db.refresh(subject)
    return subject


@router.get("/subjects", response_model=list[SubjectOut])
def list_subjects(
    department_id: int | None = None,
    semester: int | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[Subject]:
    """List subjects (read-only, own institute), filterable by department/semester."""
    stmt = select(Subject).where(Subject.tenant_id == _user.tenant_id)
    if department_id is not None:
        stmt = stmt.where(Subject.department_id == department_id)
    if semester is not None:
        stmt = stmt.where(Subject.semester == semester)
    return list(db.scalars(stmt.order_by(Subject.semester, Subject.code)))


# --- Results ---------------------------------------------------------------
@router.post("/results", response_model=ResultOut)
def upsert_result(
    payload: ResultCreate,
    db: Session = Depends(get_db),
    _teacher: User = Depends(teacher_only),
) -> Result:
    """Create or update a student's result for a subject (idempotent).

    The grade point is computed from marks_obtained / max_marks.
    """
    subject = db.get(Subject, payload.subject_id)
    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found"
        )
    student = db.get(User, payload.student_id)
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Student not found"
        )

    percentage = payload.marks_obtained / payload.max_marks * 100
    grade_point = grade_point_for(percentage)

    existing = db.scalar(
        select(Result).where(
            Result.student_id == payload.student_id,
            Result.subject_id == payload.subject_id,
        )
    )
    if existing is not None:
        existing.marks_obtained = payload.marks_obtained
        existing.max_marks = payload.max_marks
        existing.grade_point = grade_point
        record = existing
    else:
        record = Result(
            student_id=payload.student_id,
            subject_id=payload.subject_id,
            marks_obtained=payload.marks_obtained,
            max_marks=payload.max_marks,
            grade_point=grade_point,
        )
        db.add(record)

    db.commit()
    db.refresh(record)
    return record


@router.get("/me/results", response_model=list[ResultOut])
def my_results(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Result]:
    """List the logged-in user's own results."""
    return list(
        db.scalars(
            select(Result).where(Result.student_id == current_user.id)
        )
    )


@router.get("/me/summary", response_model=AcademicSummaryOut)
def my_academic_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AcademicSummaryOut:
    """Compute the logged-in user's CGPA and per-semester SGPA.

    Both are credit-weighted averages of grade points.
    """
    rows = db.execute(
        select(Result, Subject)
        .join(Subject, Result.subject_id == Subject.id)
        .where(Result.student_id == current_user.id)
    ).all()

    sem_points: dict[int, float] = defaultdict(float)
    sem_credits: dict[int, int] = defaultdict(int)
    total_points = 0.0
    total_credits = 0

    for result, subject in rows:
        sem_points[subject.semester] += result.grade_point * subject.credits
        sem_credits[subject.semester] += subject.credits
        total_points += result.grade_point * subject.credits
        total_credits += subject.credits

    semesters = [
        SemesterGPA(
            semester=sem,
            sgpa=round(sem_points[sem] / sem_credits[sem], 2)
            if sem_credits[sem]
            else 0.0,
            credits=sem_credits[sem],
        )
        for sem in sorted(sem_points)
    ]
    cgpa = round(total_points / total_credits, 2) if total_credits else 0.0
    return AcademicSummaryOut(
        cgpa=cgpa, total_credits=total_credits, semesters=semesters
    )


@router.get(
    "/subjects/{subject_id}/results",
    response_model=list[ResultOut],
    dependencies=[Depends(teacher_only)],
)
def subject_results(
    subject_id: int,
    db: Session = Depends(get_db),
) -> list[Result]:
    """List all results for a subject (teacher gradebook view)."""
    subject = db.get(Subject, subject_id)
    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found"
        )
    return list(
        db.scalars(select(Result).where(Result.subject_id == subject_id))
    )
