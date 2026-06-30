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

import csv
import io
import secrets

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from audit import record_audit
from db import get_db
from models import Department, Section, User, UserRole
from schemas import (
    AdminUserCreate,
    BulkImportResult,
    BulkImportRowResult,
    DepartmentCreate,
    DepartmentOut,
    SectionCreate,
    SectionOut,
    UserOut,
    UserRoleUpdate,
    UserSectionUpdate,
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
)
def create_user(
    payload: AdminUserCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
) -> User:
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
    db.flush()
    record_audit(
        db,
        admin,
        action="user.create",
        summary=f"Created {payload.role.value} account {payload.email}",
        target_type="user",
        target_id=user.id,
    )
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
    record_audit(
        db,
        admin,
        action="user.role_change",
        summary=f"Changed role of {user.email} to {payload.role.value}",
        target_type="user",
        target_id=user.id,
    )
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
    record_audit(
        db,
        admin,
        action="user.status_change",
        summary=f"{'Enabled' if payload.is_active else 'Disabled'} account {user.email}",
        target_type="user",
        target_id=user.id,
    )
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}/section", response_model=UserOut)
def update_user_section(
    user_id: int,
    payload: UserSectionUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
) -> User:
    """Assign a user to a section (or clear it with section_id=null).

    Builds the class roster so teachers can mark attendance and enter marks
    for the students in a section.
    """
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if payload.section_id is not None:
        section = db.get(Section, payload.section_id)
        if section is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Section not found"
            )
    user.section_id = payload.section_id
    record_audit(
        db,
        admin,
        action="user.section_assign",
        summary=(
            f"Cleared section of {user.email}"
            if payload.section_id is None
            else f"Assigned {user.email} to section #{payload.section_id}"
        ),
        target_type="user",
        target_id=user.id,
    )
    db.commit()
    db.refresh(user)
    return user


# --- Departments -----------------------------------------------------------
@router.post(
    "/departments",
    response_model=DepartmentOut,
    status_code=status.HTTP_201_CREATED,
)
def create_department(
    payload: DepartmentCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
) -> Department:
    """Create a department. Name and code must be unique within the institute."""
    dept = Department(
        tenant_id=admin.tenant_id, name=payload.name, code=payload.code
    )
    db.add(dept)
    try:
        db.flush()
        record_audit(
            db,
            admin,
            action="department.create",
            summary=f"Created department {payload.name} ({payload.code})",
            target_type="department",
            target_id=dept.id,
        )
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
    user: User = Depends(get_current_user),
) -> list[Department]:
    """List departments in the caller's institute (any logged-in user)."""
    return list(
        db.scalars(
            select(Department)
            .where(Department.tenant_id == user.tenant_id)
            .order_by(Department.code)
        )
    )


# --- Sections --------------------------------------------------------------
@router.post(
    "/departments/{department_id}/sections",
    response_model=SectionOut,
    status_code=status.HTTP_201_CREATED,
)
def create_section(
    department_id: int,
    payload: SectionCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
) -> Section:
    """Create a section inside a department. Name unique within the department."""
    department = db.get(Department, department_id)
    # Tenant guard: a department from another institute is hidden as 404.
    if department is None or department.tenant_id != admin.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Department not found"
        )
    section = Section(
        tenant_id=department.tenant_id,
        name=payload.name,
        year=payload.year,
        department_id=department_id,
    )
    db.add(section)
    try:
        db.flush()
        record_audit(
            db,
            admin,
            action="section.create",
            summary=f"Created section {payload.name} in department #{department_id}",
            target_type="section",
            target_id=section.id,
        )
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
    user: User = Depends(get_current_user),
) -> list[Section]:
    """List sections for a department (any logged-in user, own institute)."""
    department = db.get(Department, department_id)
    # Tenant guard: a department from another institute is hidden as 404.
    if department is None or department.tenant_id != user.tenant_id:
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


# --- Bulk user import ------------------------------------------------------
_MAX_BULK_ROWS = 1000


@router.get("/users/bulk-template")
def bulk_user_template(_admin: User = Depends(admin_only)) -> Response:
    """Download a sample CSV showing the columns expected by bulk import."""
    sample = (
        "full_name,email,role,password,section_id\n"
        "Asha Verma,asha.verma@campus.ai,student,,1\n"
        "Ravi Kumar,ravi.kumar@campus.ai,student,Secret123,1\n"
        "Prof Iyer,prof.iyer@campus.ai,teacher,,\n"
    )
    return Response(
        content=sample,
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                "attachment; filename=campus_users_template.csv"
            )
        },
    )


@router.post("/users/bulk-import", response_model=BulkImportResult)
async def bulk_import_users(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
) -> BulkImportResult:
    """Create many accounts at once from an uploaded CSV.

    Header row is required. Columns: full_name, email, role, password,
    section_id. `role` defaults to "student"; a password is auto-generated
    when blank (and returned once so you can share it); `section_id` is
    optional (only meaningful for students). Each row is validated on its
    own - invalid rows are skipped with a reason and never abort the rest -
    and all valid rows are committed together in one transaction.
    """
    raw = await file.read()
    try:
        text_data = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a UTF-8 encoded CSV",
        )

    reader = csv.DictReader(io.StringIO(text_data))
    if reader.fieldnames is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV is empty or missing a header row",
        )

    # Map normalised (lowercase) header names back to the originals.
    field_map = {
        (name or "").strip().lower(): name for name in reader.fieldnames
    }
    if "email" not in field_map:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV must include an 'email' column",
        )

    def cell(row: dict, key: str) -> str:
        src = field_map.get(key)
        return (row.get(src) or "").strip() if src else ""

    # Preload existing emails + valid section ids once (transaction-safe).
    existing_emails = {e.lower() for e in db.scalars(select(User.email))}
    valid_section_ids = set(db.scalars(select(Section.id)))
    valid_roles = {r.value for r in UserRole}

    results: list[BulkImportRowResult] = []
    seen_in_file: set[str] = set()
    pending: list[tuple[int, User, str | None]] = []
    total = 0

    for i, row in enumerate(reader, start=2):  # row 1 is the header
        total += 1
        if total > _MAX_BULK_ROWS:
            results.append(
                BulkImportRowResult(
                    row=i,
                    status="skipped",
                    detail=f"Exceeded the limit of {_MAX_BULK_ROWS} rows",
                )
            )
            continue

        email = cell(row, "email").lower()
        full_name = cell(row, "full_name") or cell(row, "name")
        role_raw = (cell(row, "role") or "student").lower()
        password = cell(row, "password")
        section_raw = cell(row, "section_id")

        domain = email.split("@")[-1] if "@" in email else ""
        if not email or "@" not in email or "." not in domain:
            results.append(
                BulkImportRowResult(
                    row=i,
                    email=email or None,
                    status="skipped",
                    detail="Invalid or missing email",
                )
            )
            continue
        if not full_name:
            results.append(
                BulkImportRowResult(
                    row=i,
                    email=email,
                    status="skipped",
                    detail="Missing full_name",
                )
            )
            continue
        if role_raw not in valid_roles:
            results.append(
                BulkImportRowResult(
                    row=i,
                    email=email,
                    status="skipped",
                    detail=f"Invalid role '{role_raw}'",
                )
            )
            continue
        if email in seen_in_file:
            results.append(
                BulkImportRowResult(
                    row=i,
                    email=email,
                    status="skipped",
                    detail="Duplicate email within the file",
                )
            )
            continue
        if email in existing_emails:
            results.append(
                BulkImportRowResult(
                    row=i,
                    email=email,
                    status="skipped",
                    detail="Email already registered",
                )
            )
            continue

        section_id: int | None = None
        if section_raw:
            if (
                not section_raw.isdigit()
                or int(section_raw) not in valid_section_ids
            ):
                results.append(
                    BulkImportRowResult(
                        row=i,
                        email=email,
                        status="skipped",
                        detail=f"Unknown section_id '{section_raw}'",
                    )
                )
                continue
            section_id = int(section_raw)

        generated: str | None = None
        if not password:
            password = secrets.token_urlsafe(9)
            generated = password
        elif len(password) < 6:
            results.append(
                BulkImportRowResult(
                    row=i,
                    email=email,
                    status="skipped",
                    detail="Password must be at least 6 characters",
                )
            )
            continue

        seen_in_file.add(email)
        pending.append(
            (
                i,
                User(
                    email=email,
                    full_name=full_name,
                    hashed_password=hash_password(password),
                    role=UserRole(role_raw),
                    section_id=section_id,
                ),
                generated,
            )
        )

    # Persist every valid row together, then record one audit entry.
    created_rows: list[tuple[int, int, str, UserRole, str | None]] = []
    if pending:
        for _, user, _ in pending:
            db.add(user)
        db.flush()
        for i, user, generated in pending:
            created_rows.append(
                (i, user.id, user.email, user.role, generated)
            )
        record_audit(
            db,
            admin,
            action="user.bulk_import",
            summary=f"Bulk-imported {len(pending)} user(s) from CSV",
            target_type="user",
        )
        db.commit()

    for i, uid, email, role, generated in created_rows:
        results.append(
            BulkImportRowResult(
                row=i,
                email=email,
                status="created",
                detail="Created",
                user_id=uid,
                role=role,
                temp_password=generated,
            )
        )

    results.sort(key=lambda r: r.row)
    created = sum(1 for r in results if r.status == "created")
    return BulkImportResult(
        total_rows=total,
        created=created,
        skipped=total - created,
        results=results,
    )
