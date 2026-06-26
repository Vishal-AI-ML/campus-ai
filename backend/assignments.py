"""Assignments module.

  * TEACHER/ADMIN: create assignments for a section, list them, view every
    submission, and grade each one (marks + feedback).
  * STUDENT: see their own section's assignments (with their submission state),
    submit/re-submit work, and read their grade + feedback.

Mounted under the `/assignments` prefix by `main.py`.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from db import get_db
from models import (
    Assignment,
    Section,
    Subject,
    Submission,
    SubmissionStatus,
    User,
    UserRole,
)
from schemas import (
    AssignmentCreate,
    AssignmentOut,
    AssignmentWithStatusOut,
    SubmissionCreate,
    SubmissionGrade,
    SubmissionOut,
)
from security import get_current_user, require_roles

router = APIRouter(prefix="/assignments", tags=["assignments"])

# Posting + grading is staff work (teacher or admin).
staff_only = require_roles(UserRole.teacher, UserRole.admin)


@router.post(
    "", response_model=AssignmentOut, status_code=status.HTTP_201_CREATED
)
def create_assignment(
    payload: AssignmentCreate,
    db: Session = Depends(get_db),
    staff: User = Depends(staff_only),
) -> Assignment:
    """Create an assignment for a section (optionally tied to a subject)."""
    section = db.get(Section, payload.section_id)
    if section is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Section not found"
        )
    if (
        payload.subject_id is not None
        and db.get(Subject, payload.subject_id) is None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found"
        )
    assignment = Assignment(
        section_id=payload.section_id,
        subject_id=payload.subject_id,
        title=payload.title,
        description=payload.description,
        due_date=payload.due_date,
        max_marks=payload.max_marks,
        created_by_id=staff.id,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.get(
    "",
    response_model=list[AssignmentOut],
    dependencies=[Depends(staff_only)],
)
def list_assignments(
    section_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[Assignment]:
    """List assignments (staff), optionally filtered to one section."""
    stmt = select(Assignment)
    if section_id is not None:
        stmt = stmt.where(Assignment.section_id == section_id)
    return list(db.scalars(stmt.order_by(Assignment.due_date.desc())))


@router.get("/me", response_model=list[AssignmentWithStatusOut])
def my_assignments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AssignmentWithStatusOut]:
    """The logged-in student's section assignments + their submission state."""
    if current_user.section_id is None:
        return []
    assignments = list(
        db.scalars(
            select(Assignment)
            .where(Assignment.section_id == current_user.section_id)
            .order_by(Assignment.due_date.desc())
        )
    )
    if not assignments:
        return []
    subs = {
        s.assignment_id: s
        for s in db.scalars(
            select(Submission).where(
                Submission.student_id == current_user.id,
                Submission.assignment_id.in_([a.id for a in assignments]),
            )
        )
    }
    out: list[AssignmentWithStatusOut] = []
    for a in assignments:
        item = AssignmentWithStatusOut.model_validate(a)
        sub = subs.get(a.id)
        if sub is not None:
            item.submitted = True
            item.submission_status = sub.status
            item.marks = sub.marks
        out.append(item)
    return out


@router.post("/{assignment_id}/submit", response_model=SubmissionOut)
def submit_assignment(
    assignment_id: int,
    payload: SubmissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Submission:
    """Submit (or re-submit) work. Students only, and only for an assignment in
    their own section. Re-submitting resets the row to 'submitted'."""
    assignment = db.get(Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found"
        )
    if (
        current_user.role != UserRole.student
        or current_user.section_id != assignment.section_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students of this section can submit",
        )
    if not (payload.content or payload.link):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide submission text or a link",
        )

    existing = db.scalar(
        select(Submission).where(
            Submission.assignment_id == assignment_id,
            Submission.student_id == current_user.id,
        )
    )
    now = datetime.now(timezone.utc)
    if existing is not None:
        existing.content = payload.content
        existing.link = payload.link
        existing.status = SubmissionStatus.submitted
        existing.marks = None
        existing.feedback = None
        existing.graded_by_id = None
        existing.graded_at = None
        existing.submitted_at = now
        record = existing
    else:
        record = Submission(
            assignment_id=assignment_id,
            student_id=current_user.id,
            content=payload.content,
            link=payload.link,
        )
        db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/{assignment_id}/my-submission", response_model=SubmissionOut)
def my_submission(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Submission:
    """The logged-in student's submission for one assignment (404 if none)."""
    sub = db.scalar(
        select(Submission).where(
            Submission.assignment_id == assignment_id,
            Submission.student_id == current_user.id,
        )
    )
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No submission yet"
        )
    return sub


@router.get(
    "/{assignment_id}/submissions",
    response_model=list[SubmissionOut],
    dependencies=[Depends(staff_only)],
)
def list_submissions(
    assignment_id: int,
    db: Session = Depends(get_db),
) -> list[Submission]:
    """All submissions for an assignment (teacher grading view)."""
    if db.get(Assignment, assignment_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found"
        )
    return list(
        db.scalars(
            select(Submission)
            .where(Submission.assignment_id == assignment_id)
            .order_by(Submission.submitted_at)
        )
    )


@router.patch(
    "/submissions/{submission_id}/grade", response_model=SubmissionOut
)
def grade_submission(
    submission_id: int,
    payload: SubmissionGrade,
    db: Session = Depends(get_db),
    staff: User = Depends(staff_only),
) -> Submission:
    """Assign marks + feedback to a submission (teacher/admin)."""
    sub = db.get(Submission, submission_id)
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found"
        )
    assignment = db.get(Assignment, sub.assignment_id)
    if assignment is not None and payload.marks > assignment.max_marks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Marks cannot exceed the assignment max of {assignment.max_marks}",
        )
    sub.marks = payload.marks
    sub.feedback = payload.feedback
    sub.status = SubmissionStatus.graded
    sub.graded_by_id = staff.id
    sub.graded_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(sub)
    return sub
