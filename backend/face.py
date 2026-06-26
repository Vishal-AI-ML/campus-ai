"""Face attendance - enrollment routes (backend side).

Teachers/admins enroll a student's reference face: the uploaded photo is
forwarded to the AI worker (InsightFace + Qdrant), which detects exactly one
face and upserts its 512-dim embedding keyed by the student's id. We persist
only a lightweight enrollment *record* here (who enrolled, when, and the
detection confidence) - the embedding itself never touches Postgres, it lives
in the vector store.

Reads (enrollment status per roster) are open to all staff roles; enrolling or
removing a face is teacher/admin only. Mounted under the `/face` prefix by
`main.py`.

Location:
    E:\\campus-ai\\backend\\face.py
"""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

import ai_client
from db import get_db
from models import FaceEnrollment, Section, User, UserRole
from schemas import FaceEnrollRequest, FaceEnrollmentOut, FaceEnrollmentStatusOut
from security import require_roles

router = APIRouter(prefix="/face", tags=["face"])

# Enrolling/removing a face is teacher or admin work; reads also allow the TPO.
enroll_roles = require_roles(UserRole.teacher, UserRole.admin)
staff_roles = require_roles(UserRole.teacher, UserRole.tpo, UserRole.admin)


def _worker_error(exc: Exception) -> HTTPException:
    """Map an AI-worker call failure to a clean HTTP error for the client.

    A worker HTTP error (e.g. 422 'zero or multiple faces') is surfaced with
    its own status + detail; a transport failure means the worker is down.
    """
    if isinstance(exc, httpx.HTTPStatusError):
        detail = "Face worker rejected the request."
        try:
            detail = exc.response.json().get("detail", detail)
        except Exception:  # noqa: BLE001 - fall back to the generic message
            pass
        return HTTPException(status_code=exc.response.status_code, detail=detail)
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="AI face worker is unavailable. Make sure it is running on :8100.",
    )


@router.post("/enroll", response_model=FaceEnrollmentOut)
def enroll_face(
    payload: FaceEnrollRequest,
    db: Session = Depends(get_db),
    staff: User = Depends(enroll_roles),
) -> FaceEnrollment:
    """Enroll a student's reference face (teacher/admin).

    The photo must contain exactly one clear, front-facing face - the worker
    enforces this and returns 422 otherwise. Re-enrolling the same student
    overwrites both the stored embedding (in Qdrant) and this record.

    Note: the very first enrollment after a worker restart also triggers the
    one-time InsightFace model download (~300 MB), so it can take a while.
    """
    student = db.get(User, payload.student_id)
    if student is None or student.role != UserRole.student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Student not found"
        )

    try:
        result = ai_client.enroll_face(payload.student_id, payload.image_base64)
    except Exception as exc:  # noqa: BLE001 - mapped to a clean HTTP error
        raise _worker_error(exc)

    det_score = result.get("det_score")
    record = db.get(FaceEnrollment, payload.student_id)
    if record is None:
        record = FaceEnrollment(
            student_id=payload.student_id,
            enrolled_by_id=staff.id,
            det_score=det_score,
        )
        db.add(record)
    else:
        # Re-enrollment: refresh who/when (via onupdate) + the detection score.
        record.enrolled_by_id = staff.id
        record.det_score = det_score
    db.commit()
    db.refresh(record)
    return record


@router.get(
    "/enrollments",
    response_model=list[FaceEnrollmentStatusOut],
    dependencies=[Depends(staff_roles)],
)
def list_enrollments(
    section_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[FaceEnrollmentStatusOut]:
    """List students + whether each has an enrolled face.

    Pass ?section_id=<id> to scope the roster to one section (e.g. the class a
    teacher is about to take attendance for). Powers the enrollment-roster UI.
    """
    stmt = select(User).where(User.role == UserRole.student)
    if section_id is not None:
        section = db.get(Section, section_id)
        if section is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Section not found"
            )
        stmt = stmt.where(User.section_id == section_id)
    students = list(db.scalars(stmt.order_by(User.full_name)))

    enrolled = {e.student_id: e for e in db.scalars(select(FaceEnrollment))}
    return [
        FaceEnrollmentStatusOut(
            student_id=s.id,
            full_name=s.full_name,
            email=s.email,
            enrolled=s.id in enrolled,
            det_score=enrolled[s.id].det_score if s.id in enrolled else None,
            enrolled_at=enrolled[s.id].enrolled_at if s.id in enrolled else None,
        )
        for s in students
    ]


@router.delete("/enroll/{student_id}")
def remove_enrollment(
    student_id: int,
    db: Session = Depends(get_db),
    staff: User = Depends(enroll_roles),
) -> dict:
    """Remove a student's enrolled face from both the worker (Qdrant) and here.

    Idempotent: deleting a student who was never enrolled still returns OK.
    """
    try:
        ai_client.delete_face_enrollment(student_id)
    except Exception as exc:  # noqa: BLE001
        raise _worker_error(exc)
    record = db.get(FaceEnrollment, student_id)
    if record is not None:
        db.delete(record)
        db.commit()
    return {"student_id": student_id, "deleted": True}
