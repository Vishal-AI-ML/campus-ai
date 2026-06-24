"""Admin routes: manage users and the institute's structure.

Sections:
  * Users        - list / create / change role / enable-disable accounts
  * Departments  - top-level academic units
  * Sections     - classes within a department

NOTE: Subjects are managed by TEACHERS (curriculum), not admins - see the
academics routes. All write operations here are admin-only via
`require_roles(UserRole.admin)`; reads require a valid login. Mounted under the
`/admin` prefix by `main.py`.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db import get_db
from models import Department, Section, User, UserRole
from schemas import (
    AdminUserCreate,
    DepartmentCreate,
    DepartmentOut,
    SectionCreate,
    SectionOut,
    UserOut,
    UserRoleUpdate,
    UserStatusUpdate,
)
from security import get_current_user, hash_password, require_roles

router = APIRouter(prefix="/admin", tags=["admin"])

# Reusable dependency: only admins may pass.
admin_only = require_roles(UserRole.admin)


# --- Users -----------------------------------------------------------------
@router.get(
    "/users", response_model=list[UserOut], dependencies=[Depends(admin_only)]
)
def list_users(
    role: UserRole | None = None,
    db: Session = Depends(get_db),
) -> list[User]:
    """List users, optionally filtered by role (e.g. ?role=student)."""
    stmt = select(User).order_by(User.id)
    if role is not None:
        stmt = stmt.where(User.role == role)
    return list(db.scalars(stmt))


@router.post(
    "/users",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(admin_only)],
)
def create_user(payload: AdminUserCreate, db: Session = Depends(get_db)) -> User:
    """Create an account with an explicit role. Email must be unique."""
    exists = db.scalar(select(User).where(User.email == payload.email))
    if exists is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}/role", response_model=UserOut)
def update_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
) -> User:
    """Change a user's role. An admin cannot change their own role (lockout guard)."""
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own role",
        )
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    user.role = payload.role
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}/status", response_model=UserOut)
def update_user_status(
    user_id: int,
    payload: UserStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
) -> User:
    """Enable/disable an account. An admin cannot disable themselves."""
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own status",
        )
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    user.is_active = payload.is_active
    db.commit()
    db.refresh(user)
    return user


# --- Departments -----------------------------------------------------------
@router.post(
    "/departments",
    response_model=DepartmentOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(admin_only)],
)
def create_department(payload: DepartmentCreate, db: Session = Depends(get_db)) -> Department:
    """Create a department. Name and code must both be unique."""
    dept = Department(name=payload.name, code=payload.code)
    db.add(dept)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A department with this name or code already exists",
        )
    db.refresh(dept)
    return dept


@router.get("/departments", response_model=list[DepartmentOut])
def list_departments(
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
) -> list[Department]:
    """List all departments (any logged-in user)."""
    return list(db.scalars(select(Department).order_by(Department.code)))


# --- Sections --------------------------------------------------------------
@router.post(
    "/departments/{department_id}/sections",
    response_model=SectionOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(admin_only)],
)
def create_section(
    department_id: int,
    payload: SectionCreate,
    db: Session = Depends(get_db),
) -> Section:
    """Create a section inside a department. Name unique within the department."""
    department = db.get(Department, department_id)
    if department is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Department not found"
        )
    section = Section(
        name=payload.name, year=payload.year, department_id=department_id
    )
    db.add(section)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A section with this name already exists in this department",
        )
    db.refresh(section)
    return section


@router.get(
    "/departments/{department_id}/sections", response_model=list[SectionOut]
)
def list_sections(
    department_id: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
) -> list[Section]:
    """List sections for a department (any logged-in user)."""
    department = db.get(Department, department_id)
    if department is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Department not found"
        )
    return list(
        db.scalars(
            select(Section)
            .where(Section.department_id == department_id)
            .order_by(Section.name)
        )
    )
