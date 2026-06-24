"""SQLAlchemy ORM models for Campus AI.

Tables so far:
  * users               - accounts + roles (auth/RBAC backbone)
  * departments         - top-level academic units (e.g. CSE, ECE)
  * sections            - a class/section inside a department
  * attendance_records  - one row per student, per section, per date
  * subjects            - a subject/course inside a department
  * results             - a student's marks + grade point for one subject
  * skills              - a student's claimed skill + proof + verification state
  * projects            - a project (individual or group) + proof links
  * project_members     - one row per contributor, verified individually
  * drives              - placement/recruitment drives + eligibility criteria
  * applications        - a student's application to a drive + its status

SQLAlchemy 2.x typed-mapping style (`Mapped` / `mapped_column`).
"""

import enum
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import Base


class UserRole(str, enum.Enum):
    """The four core roles in Campus AI (drives RBAC across the product)."""

    student = "student"
    teacher = "teacher"
    tpo = "tpo"
    admin = "admin"


class AttendanceStatus(str, enum.Enum):
    """Possible states when marking a student for a given day."""

    present = "present"
    absent = "absent"
    late = "late"


class SkillStatus(str, enum.Enum):
    """Shared verification lifecycle for proof-backed achievements.

    Used by both `skills` and `project_members` (the anti-fraud moat):
      pending  -> claimed, awaiting mentor review
      verified -> mentor confirmed the proof; counts toward resume/eligibility
      flagged  -> mentor rejected/doubted the proof; does NOT count
    """

    pending = "pending"
    verified = "verified"
    flagged = "flagged"


class ApplicationStatus(str, enum.Enum):
    """Lifecycle of a student's application to a placement drive.

      applied     -> student applied (was eligible at apply time)
      shortlisted -> TPO shortlisted the candidate for the next round
      selected    -> candidate was selected/placed
      rejected    -> TPO rejected the application
    """

    applied = "applied"
    shortlisted = "shortlisted"
    selected = "selected"
    rejected = "rejected"


class User(Base):
    """A single account. One row per person, regardless of role."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        default=UserRole.student,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role.value}>"


class Department(Base):
    """A top-level academic unit, e.g. 'Computer Science' (code 'CSE')."""

    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    sections: Mapped[list["Section"]] = relationship(
        back_populates="department", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Department id={self.id} code={self.code!r}>"


class Section(Base):
    """A class/section within a department, e.g. name 'A', year 3."""

    __tablename__ = "sections"
    __table_args__ = (
        UniqueConstraint("department_id", "name", name="uq_section_dept_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    department: Mapped["Department"] = relationship(back_populates="sections")

    def __repr__(self) -> str:
        return f"<Section id={self.id} name={self.name!r} dept={self.department_id}>"


class AttendanceRecord(Base):
    """One attendance entry: a student's status in a section on a date.

    A student can have at most one record per section per date (enforced by a
    unique constraint), so re-marking simply updates the existing row.
    """

    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "section_id",
            "date",
            name="uq_attendance_student_section_date",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    section_id: Mapped[int] = mapped_column(
        ForeignKey("sections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[AttendanceStatus] = mapped_column(
        Enum(AttendanceStatus, name="attendance_status"), nullable=False
    )
    marked_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<Attendance student={self.student_id} section={self.section_id} "
            f"date={self.date} status={self.status.value}>"
        )


class Subject(Base):
    """A subject/course within a department, tied to a semester.

    Subject code is unique *within* a department, so two departments can reuse
    the same code.
    """

    __tablename__ = "subjects"
    __table_args__ = (
        UniqueConstraint("department_id", "code", name="uq_subject_dept_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    credits: Mapped[int] = mapped_column(Integer, nullable=False)
    semester: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Subject id={self.id} code={self.code!r} sem={self.semester}>"


class Result(Base):
    """A student's result for one subject: marks + a 0-10 grade point.

    `grade_point` is derived from the percentage by the academics module, so
    SGPA/CGPA can be computed as a credit-weighted average.
    One result per student per subject (unique constraint).
    """

    __tablename__ = "results"
    __table_args__ = (
        UniqueConstraint("student_id", "subject_id", name="uq_result_student_subject"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    marks_obtained: Mapped[float] = mapped_column(Float, nullable=False)
    max_marks: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    grade_point: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<Result student={self.student_id} subject={self.subject_id} "
            f"gp={self.grade_point}>"
        )


class Skill(Base):
    """A student-claimed skill plus its proof and verification state.

    This is the core of the 'verified data moat': a skill only counts once a
    mentor marks it `verified`. `ai_score` is left NULL here and filled later
    by the AI worker (proof analysis).
    A student cannot claim the same skill name twice (unique constraint).
    """

    __tablename__ = "skills"
    __table_args__ = (
        UniqueConstraint("student_id", "name", name="uq_skill_student_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    evidence_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    evidence_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[SkillStatus] = mapped_column(
        Enum(SkillStatus, name="skill_status"),
        default=SkillStatus.pending,
        nullable=False,
        index=True,
    )
    # Filled later by the AI worker (0-100 confidence that the proof is real).
    ai_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    reviewed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    review_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<Skill student={self.student_id} name={self.name!r} "
            f"status={self.status.value}>"
        )


class Project(Base):
    """A project (individual or group) with proof links.

    The project record itself is just metadata + evidence; the actual
    verification happens per contributor in `project_members`, so a group
    project credits only the members a mentor has individually verified.
    """

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Comma-separated tech list, e.g. 'FastAPI, PostgreSQL, Docker'.
    tech_stack: Mapped[str | None] = mapped_column(String(300), nullable=True)
    repo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    demo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_group: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    members: Mapped[list["ProjectMember"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Project id={self.id} title={self.title!r} group={self.is_group}>"


class ProjectMember(Base):
    """One contributor on a project, verified individually (anti-freeloader).

    Reuses the shared `skill_status` enum type for its verification lifecycle
    (the type is created by the skills migration; `create_type=False` here so
    this table does not try to recreate it).
    A student appears at most once per project (unique constraint).
    """

    __tablename__ = "project_members"
    __table_args__ = (
        UniqueConstraint("project_id", "student_id", name="uq_project_member"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # What this member actually did on the project (their claim to verify).
    contribution: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[SkillStatus] = mapped_column(
        Enum(SkillStatus, name="skill_status", create_type=False),
        default=SkillStatus.pending,
        nullable=False,
        index=True,
    )
    # Filled later by the AI worker (0-100 confidence that the proof is real).
    ai_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    reviewed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    review_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    project: Mapped["Project"] = relationship(back_populates="members")

    def __repr__(self) -> str:
        return (
            f"<ProjectMember project={self.project_id} student={self.student_id} "
            f"status={self.status.value}>"
        )


class Drive(Base):
    """A placement/recruitment drive posted by the TPO.

    Eligibility criteria live as columns; the engine checks each student's
    VERIFIED profile (CGPA, attendance, verified skills, verified projects)
    against them. Only verified data counts - the moat reaches placement too.
    """

    __tablename__ = "drives"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role_title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(150), nullable=True)
    # CTC in lakhs per annum (LPA).
    package_lpa: Mapped[float | None] = mapped_column(Float, nullable=True)

    # --- Eligibility criteria (checked against each student's VERIFIED data) ---
    min_cgpa: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    min_attendance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    min_verified_projects: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    # Comma-separated required skill names, matched against verified skills.
    required_skills: Mapped[str | None] = mapped_column(String(500), nullable=True)

    is_open: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    applications: Mapped[list["Application"]] = relationship(
        back_populates="drive", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<Drive id={self.id} company={self.company_name!r} "
            f"open={self.is_open}>"
        )


class Application(Base):
    """A student's application to a drive, plus the TPO's decision.

    A student can apply to a drive at most once (unique constraint). Only
    students who pass the drive's eligibility check at apply time can create
    one - the verified-data moat gates the application itself.
    """

    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint(
            "drive_id", "student_id", name="uq_application_drive_student"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    drive_id: Mapped[int] = mapped_column(
        ForeignKey("drives.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="application_status"),
        default=ApplicationStatus.applied,
        nullable=False,
        index=True,
    )
    # Optional TPO note attached when shortlisting/selecting/rejecting.
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    decided_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    drive: Mapped["Drive"] = relationship(back_populates="applications")

    def __repr__(self) -> str:
        return (
            f"<Application drive={self.drive_id} student={self.student_id} "
            f"status={self.status.value}>"
        )
