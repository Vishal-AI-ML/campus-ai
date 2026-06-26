"""Study Hub (materials) module.

  * TEACHER/ADMIN: upload study material/notes for a section (optionally tied
    to a subject), list a section's materials, and delete uploads (admins any,
    teachers only their own).
  * STUDENT: browse their own section's materials (optionally filtered by
    subject) and open a single item.

Material is link-based (an external URL) and/or inline notes text - there is no
file storage yet (signed-URL uploads can be added later). Mounted under the
`/materials` prefix by `main.py`.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from db import get_db
from models import Material, Section, Subject, User, UserRole
from schemas import MaterialCreate, MaterialOut
from security import get_current_user, require_roles

router = APIRouter(prefix="/materials", tags=["materials"])

# Uploading + deleting material is staff work (teacher or admin).
staff_only = require_roles(UserRole.teacher, UserRole.admin)


@router.post("", response_model=MaterialOut, status_code=status.HTTP_201_CREATED)
def create_material(
    payload: MaterialCreate,
    db: Session = Depends(get_db),
    staff: User = Depends(staff_only),
) -> Material:
    """Upload a study material for a section (optionally tied to a subject)."""
    if not (payload.content or payload.link):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide notes content or a resource link",
        )
    if db.get(Section, payload.section_id) is None:
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
    material = Material(
        section_id=payload.section_id,
        subject_id=payload.subject_id,
        title=payload.title,
        description=payload.description,
        content=payload.content,
        link=payload.link,
        category=payload.category,
        uploaded_by_id=staff.id,
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


@router.get(
    "",
    response_model=list[MaterialOut],
    dependencies=[Depends(staff_only)],
)
def list_materials(
    section_id: int | None = None,
    subject_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[Material]:
    """List materials (staff), optionally filtered by section and/or subject."""
    stmt = select(Material)
    if section_id is not None:
        stmt = stmt.where(Material.section_id == section_id)
    if subject_id is not None:
        stmt = stmt.where(Material.subject_id == subject_id)
    return list(db.scalars(stmt.order_by(Material.created_at.desc())))


@router.get("/me", response_model=list[MaterialOut])
def my_materials(
    subject_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Material]:
    """The logged-in student's section materials (optionally by subject)."""
    if current_user.section_id is None:
        return []
    stmt = select(Material).where(
        Material.section_id == current_user.section_id
    )
    if subject_id is not None:
        stmt = stmt.where(Material.subject_id == subject_id)
    return list(db.scalars(stmt.order_by(Material.created_at.desc())))


@router.get("/{material_id}", response_model=MaterialOut)
def get_material(
    material_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Material:
    """Open a single material. Students may only read their own section's."""
    material = db.get(Material, material_id)
    if material is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Material not found"
        )
    is_staff = current_user.role in (
        UserRole.teacher,
        UserRole.admin,
        UserRole.tpo,
    )
    if not is_staff and material.section_id != current_user.section_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to view this material",
        )
    return material


@router.delete("/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_material(
    material_id: int,
    db: Session = Depends(get_db),
    staff: User = Depends(staff_only),
) -> None:
    """Delete a material. Admins can delete any; teachers only their own."""
    material = db.get(Material, material_id)
    if material is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Material not found"
        )
    if staff.role != UserRole.admin and material.uploaded_by_id != staff.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own uploads",
        )
    db.delete(material)
    db.commit()
