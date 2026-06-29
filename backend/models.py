"""SQLAlchemy ORM models for Campus AI.

Tables so far:
  * users               - accounts + roles (auth/RBAC backbone)
  * departments         - top-level academic units (e.g. CSE, ECE)
  * sections            - a class/section inside a department
  * attendance_records  - one row per student, per section, per date
  * face_enrollments    - a student's enrolled reference face (embedding in Qdrant)
  * subjects            - a subject/course inside a department
  * results             - a student's marks + grade point for one subject
  * skills              - a student's claimed skill + proof + verification state
  * projects            - a project (individual or group) + proof links
  * project_members     - one row per contributor, verified individually
  * drives              - placement/recruitment drives + eligibility criteria
  * applications        - a student's application to a drive + its status
  * leads               - public demo-request/contact leads (no FK; prospects)
  * feedback            - anonymous in-product feedback

SQLAlchemy 2.x typed-mapping style (`Mapped` / `mapped_column`).
"""

import enum
from datetime import date, datetime, time

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
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import Base


class UserRole(str, enum.Enum):
    """The core roles in Campus AI (drives RBAC across the product)."""

    student = "student"
    teacher = "teacher"
    tpo = "tpo"
    admin = "admin"
    # External-facing role: recruiters from companies that hire via the portal.
    recruiter = "recruiter"


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


class RecruiterDecision(str, enum.Enum):
    """A recruiter's NON-binding assessment of a candidate they can see.

    The TPO still owns the official `ApplicationStatus`; this is the company's
    signal back to the TPO (and the natural precursor to extending an offer):
      pending    -> recruiter hasn't acted yet (default)
      interested -> wants to move forward (likely to make an offer)
      on_hold    -> keeping the candidate in consideration for now
      rejected   -> not interested (the recruiter's own view, not the TPO's)
    """

    pending = "pending"
    interested = "interested"
    on_hold = "on_hold"
    rejected = "rejected"


class OfferStatus(str, enum.Enum):
    """Lifecycle of a formal offer a recruiter extends to a candidate.

      extended  -> recruiter made the offer; awaiting the student's response
      accepted  -> student accepted the offer
      declined  -> student declined the offer
      withdrawn -> recruiter pulled the offer back (only while still extended)
    """

    extended = "extended"
    accepted = "accepted"
    declined = "declined"
    withdrawn = "withdrawn"


class Tenant(Base):
    """A single tenant = one institute/college on the platform.

    Multi-tenancy backbone. Every tenant-scoped row will carry a `tenant_id`
    pointing here, so one institute can never see or touch another's data.
    """

    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Human-readable institute name, e.g. "IIT Delhi".
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Short unique code used at signup / in a subdomain, e.g. "iitd".
    slug: Mapped[str] = mapped_column(
        String(63), unique=True, index=True, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Tenant id={self.id} slug={self.slug!r}>"


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
    # A student's class/section - used to build attendance rosters & gradebook.
    # Nullable: staff accounts (teacher/tpo/admin) and not-yet-assigned students.
    section_id: Mapped[int | None] = mapped_column(
        ForeignKey("sections.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Multi-tenancy: which institute this account belongs to.
    # NOT NULL (Phase 2d): every user belongs to exactly one tenant. All three
    # creation paths set it - invite-accept, tenant-scoped /auth/register, and
    # the Phase 1 backfill - so orphan (tenant-less) users are impossible.
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
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


class FaceEnrollment(Base):
    """A student's enrolled reference face (one row per student).

    The 512-dim face embedding itself lives in Qdrant, keyed by the student's
    id; this row records WHO is enrolled, who enrolled them, the detection
    confidence, and when - so staff rosters can show enrollment status without
    querying the vector store per student. Deleting the user cascades here.
    """

    __tablename__ = "face_enrollments"

    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    enrolled_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    det_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<FaceEnrollment student={self.student_id} "
            f"det_score={self.det_score}>"
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
    # Tenant (institute) this skill belongs to. Mirrors the student's tenant,
    # but is stored on the row so every query can filter by it directly (and so
    # a future Postgres RLS policy can enforce isolation at the DB layer too).
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
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
    # Tenant (institute) this project belongs to - the owner's institute. Every
    # member must belong to the same institute, so the whole project (and all
    # its member rows) is scoped to a single tenant.
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
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
    # Tenant (institute) of the parent project. Mirrored onto each member row so
    # the review queue and staff reads can filter by tenant directly.
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
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


class ECACategory(str, enum.Enum):
    """Buckets for extra-curricular activities (the 'well-rounded' picture)."""

    sports = "sports"
    cultural = "cultural"
    technical = "technical"
    volunteering = "volunteering"
    leadership = "leadership"
    other = "other"


class InternshipType(str, enum.Enum):
    """Kind of verifiable work-experience entry a student can log."""

    internship = "internship"
    ojt = "ojt"
    apprenticeship = "apprenticeship"
    training = "training"
    other = "other"


class ExtraCurricular(Base):
    """A student-claimed extra-curricular activity + proof + verification state.

    Same 'verified data moat' lifecycle as skills (reuses `SkillStatus`): a
    claim counts toward the resume/profile only once a teacher/TPO marks it
    `verified`. Categorised (sports/cultural/...) so recruiters see a
    well-rounded, *verified* picture beyond academics.
    A student cannot log the same activity title twice (unique constraint).
    """

    __tablename__ = "extracurriculars"
    __table_args__ = (
        UniqueConstraint("student_id", "title", name="uq_eca_student_title"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    category: Mapped[ECACategory] = mapped_column(
        Enum(ECACategory, name="eca_category"),
        default=ECACategory.other,
        nullable=False,
        index=True,
    )
    organization: Mapped[str | None] = mapped_column(String(150), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[SkillStatus] = mapped_column(
        Enum(SkillStatus, name="skill_status"),
        default=SkillStatus.pending,
        nullable=False,
        index=True,
    )
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
            f"<ExtraCurricular student={self.student_id} title={self.title!r} "
            f"status={self.status.value}>"
        )


class Internship(Base):
    """A student-claimed internship / OJT / training + proof + verification.

    Reuses the same verified-data moat as skills/ECA (`SkillStatus`): an entry
    counts toward the resume/recruiter profile only once a teacher/TPO marks it
    `verified`. Captures real work experience (org, role, dates, mode) so the
    profile shows verifiable industry exposure beyond academics. A student
    cannot log the same (organization, role) pair twice (unique constraint).
    """

    __tablename__ = "internships"
    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "organization",
            "role_title",
            name="uq_internship_student_org_role",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Tenant (institute) this internship belongs to. Mirrors the student's
    # tenant; stored on the row so every query can filter by it directly.
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization: Mapped[str] = mapped_column(String(200), nullable=False)
    role_title: Mapped[str] = mapped_column(String(150), nullable=False)
    internship_type: Mapped[InternshipType] = mapped_column(
        Enum(InternshipType, name="internship_type"),
        default=InternshipType.internship,
        nullable=False,
        index=True,
    )
    mode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    location: Mapped[str | None] = mapped_column(String(150), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    skills_used: Mapped[str | None] = mapped_column(String(300), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_ongoing: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    certificate_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    status: Mapped[SkillStatus] = mapped_column(
        Enum(SkillStatus, name="skill_status"),
        default=SkillStatus.pending,
        nullable=False,
        index=True,
    )
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
            f"<Internship student={self.student_id} org={self.organization!r} "
            f"role={self.role_title!r} status={self.status.value}>"
        )


class Resume(Base):
    """A saved, versioned snapshot of a student's AI-generated resume.

    Every call to POST /resume/generate stores one immutable version here, so a
    student keeps a history, can reopen/compare past drafts, rename them, and
    mark ONE as their primary copy. The Markdown is built only from VERIFIED
    data (same moat as the live generator), so stored versions never contain
    unproven claims.

    At most one version per student is `is_primary` at a time (enforced in the
    router when toggling, not by a DB constraint).
    """

    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Tenant (institute) this resume version belongs to. Mirrors the student's
    # tenant; stored on the row so every query can filter by it directly.
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # A friendly label (auto-generated on save, editable later).
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    # The role this draft was tailored for, if any (for context in the list).
    target_role: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # The full Markdown resume content (the actual saved document).
    markdown: Mapped[str] = mapped_column(Text, nullable=False)
    # Which LLM provider produced it (groq | gemini | ...), for transparency.
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # The student's chosen "current" resume (at most one true per student).
    is_primary: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<Resume id={self.id} student={self.student_id} "
            f"title={self.title!r} primary={self.is_primary}>"
        )


class Drive(Base):
    """A placement/recruitment drive posted by the TPO.

    Eligibility criteria live as columns; the engine checks each student's
    VERIFIED profile (CGPA, attendance, verified skills, verified projects)
    against them. Only verified data counts - the moat reaches placement too.
    """

    __tablename__ = "drives"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Tenant (institute) that posted this drive (the TPO's institute). Students
    # only ever see and apply to drives from their own institute.
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
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

    # Optional link to a recruiting company (Step 27.2). When set, that
    # company's HR can view this drive's shortlisted/selected candidates.
    recruiter_id: Mapped[int | None] = mapped_column(
        ForeignKey("recruiters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
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
    # Privacy gate (Step 27.2): a recruiter sees the candidate's contact
    # (email) only after the TPO explicitly reveals it for this application.
    contact_revealed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    # Recruiter's own (non-binding) call on this candidate (Step 27.3). The
    # TPO still owns `status`; this is the company's signal + offer precursor.
    recruiter_decision: Mapped[RecruiterDecision] = mapped_column(
        Enum(RecruiterDecision, name="recruiter_decision"),
        default=RecruiterDecision.pending,
        nullable=False,
    )
    recruiter_decision_note: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    recruiter_decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    drive: Mapped["Drive"] = relationship(back_populates="applications")
    offer: Mapped["Offer | None"] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        uselist=False,
    )

    def __repr__(self) -> str:
        return (
            f"<Application drive={self.drive_id} student={self.student_id} "
            f"status={self.status.value}>"
        )


class Offer(Base):
    """A formal offer a recruiter extends to a candidate (Step 27.3).

    One offer per application (unique). The recruiter sets the terms (role,
    package, location, joining + expiry dates); the student accepts or declines.
    The recruiter may withdraw it while it is still `extended`. A withdrawn or
    declined offer's row is reused if the recruiter later re-extends.
    """

    __tablename__ = "offers"
    __table_args__ = (
        UniqueConstraint("application_id", name="uq_offer_application"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recruiter_id: Mapped[int] = mapped_column(
        ForeignKey("recruiters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    drive_id: Mapped[int] = mapped_column(
        ForeignKey("drives.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    role_title: Mapped[str] = mapped_column(String(200), nullable=False)
    package_lpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    location: Mapped[str | None] = mapped_column(String(150), nullable=True)
    joining_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expires_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[OfferStatus] = mapped_column(
        Enum(OfferStatus, name="offer_status"),
        default=OfferStatus.extended,
        nullable=False,
        index=True,
    )
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    student_response_note: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    application: Mapped["Application"] = relationship(back_populates="offer")

    def __repr__(self) -> str:
        return (
            f"<Offer id={self.id} application={self.application_id} "
            f"status={self.status.value}>"
        )


class Lead(Base):
    """A demo-request/contact lead captured from the public marketing site.

    These are unauthenticated, public submissions (prospects, not users yet),
    so there are no foreign keys. The admin reviews them and flips `handled`.
    """

    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    institute: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    handled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Lead id={self.id} email={self.email!r} handled={self.handled}>"


class Feedback(Base):
    """Anonymous in-product feedback.

    Stored without a user link so it can be submitted from anywhere (including
    logged-out surfaces). `rating` is an optional 1-5 score.
    """

    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Feedback id={self.id} rating={self.rating}>"


class Announcement(Base):
    """An institute broadcast posted by an admin to everyone or one role.

    `audience` is one of "all", "student", "teacher", "tpo": a reader sees an
    announcement when it targets everyone or their own role. Stored as a short
    string (not an Enum) so new audiences can be added without a DB migration.
    The author link is SET NULL so deleting an admin keeps historical posts.
    """

    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Tenant (institute) this announcement was posted in. Readers only ever see
    # announcements from their own institute.
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # "all" | "student" | "teacher" | "tpo" - who should see this announcement.
    audience: Mapped[str] = mapped_column(
        String(20), default="all", nullable=False, index=True
    )
    author_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<Announcement id={self.id} title={self.title!r} "
            f"audience={self.audience}>"
        )


class CalendarEvent(Base):
    """An academic-calendar entry posted by an admin.

    `category` is one of "holiday", "exam", "event", "deadline" (drives the
    colour/label in the UI). Like announcements, `audience` is a short string
    ("all" | "student" | "teacher" | "tpo") so a reader sees entries meant for
    everyone or their own role. An optional `end_date` supports multi-day
    entries (exam weeks, holidays). Both stored as plain strings (no Enum) so
    new categories/audiences need no DB migration.
    """

    __tablename__ = "calendar_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # "holiday" | "exam" | "event" | "deadline"
    category: Mapped[str] = mapped_column(
        String(20), default="event", nullable=False
    )
    # "all" | "student" | "teacher" | "tpo" - who should see this entry.
    audience: Mapped[str] = mapped_column(
        String(20), default="all", nullable=False, index=True
    )
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<CalendarEvent id={self.id} title={self.title!r} "
            f"date={self.event_date}>"
        )


class AuditLog(Base):
    """Append-only record of a governance action (for compliance / traceability).

    Written via `record_audit()` whenever an admin changes something sensitive
    (roles, account status, structure, etc.). `actor_email` is denormalised so
    the trail survives even if the acting user is later deleted (then
    `actor_id` becomes NULL). Rows are never updated or deleted in normal use.
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # Snapshot of the actor's email so the trail is readable after user deletion.
    actor_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Machine-readable key, e.g. "user.role_change", "department.create".
    action: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    # What was acted on, e.g. "user", "department", "section".
    target_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # Human-readable one-line description shown in the UI.
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action={self.action!r}>"


# --- Assignments -----------------------------------------------------------
class SubmissionStatus(str, enum.Enum):
    """Lifecycle of a student's submission to an assignment.

      submitted -> student turned it in (re-submitting resets grading)
      graded    -> teacher assigned marks + (optional) feedback
    """

    submitted = "submitted"
    graded = "graded"


class Assignment(Base):
    """An assignment a teacher posts for a whole section (optionally tied to a
    subject). Students in that section submit work against it."""

    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Tenant (institute) of the posting teacher. Mirrored here so reads can
    # filter by institute directly.
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    section_id: Mapped[int] = mapped_column(
        ForeignKey("sections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id: Mapped[int | None] = mapped_column(
        ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    max_marks: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<Assignment id={self.id} title={self.title!r} "
            f"section={self.section_id}>"
        )


class Submission(Base):
    """A student's submission to an assignment (one per student per assignment).

    Re-submitting updates the same row and resets it to 'submitted', clearing
    any earlier grade so the teacher reviews the new work.
    """

    __tablename__ = "submissions"
    __table_args__ = (
        UniqueConstraint(
            "assignment_id",
            "student_id",
            name="uq_submission_assignment_student",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(
        ForeignKey("assignments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus, name="submission_status"),
        default=SubmissionStatus.submitted,
        nullable=False,
    )
    marks: Mapped[float | None] = mapped_column(Float, nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    graded_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    graded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<Submission id={self.id} assignment={self.assignment_id} "
            f"student={self.student_id} status={self.status.value}>"
        )



class MaterialCategory(str, enum.Enum):
    """How a Study Hub material is classified (for browsing/filtering)."""

    notes = "notes"
    slides = "slides"
    video = "video"
    link = "link"
    other = "other"


class Material(Base):
    """A study material/resource shared with a section in the Study Hub.

    Teachers (and admins) upload reference material for a section, optionally
    tied to a subject. The payload is link-based (an external URL such as a
    Drive/PDF/YouTube link) and/or inline notes text - no file storage yet
    (signed-URL uploads can be added later). Students of that section browse
    these read-only.
    """

    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Tenant (institute) of the uploading staff. Mirrored here so reads can
    # filter by institute directly.
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    section_id: Mapped[int] = mapped_column(
        ForeignKey("sections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id: Mapped[int | None] = mapped_column(
        ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Inline notes body and/or an external resource link; at least one is
    # required (validated at the API layer).
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    category: Mapped[MaterialCategory] = mapped_column(
        Enum(MaterialCategory, name="material_category"),
        default=MaterialCategory.notes,
        nullable=False,
        index=True,
    )
    uploaded_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<Material id={self.id} title={self.title!r} "
            f"section={self.section_id} category={self.category.value}>"
        )


class DoubtStatus(str, enum.Enum):
    """Lifecycle of a question in the doubt forum.

      open     -> awaiting a satisfactory answer
      resolved -> the asker (or staff) accepted an answer as the solution
    """

    open = "open"
    resolved = "resolved"


class Doubt(Base):
    """A question posted to a section's doubt forum.

    Posted by a student (only in their own section) or by staff (any section),
    and optionally tied to a subject. Becomes `resolved` when one of its
    answers is accepted.
    """

    __tablename__ = "doubts"

    id: Mapped[int] = mapped_column(primary_key=True)
    section_id: Mapped[int] = mapped_column(
        ForeignKey("sections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject_id: Mapped[int | None] = mapped_column(
        ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[DoubtStatus] = mapped_column(
        Enum(DoubtStatus, name="doubt_status"),
        default=DoubtStatus.open,
        nullable=False,
        index=True,
    )
    asked_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    answers: Mapped[list["DoubtAnswer"]] = relationship(
        back_populates="doubt", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<Doubt id={self.id} section={self.section_id} "
            f"status={self.status.value}>"
        )


class DoubtAnswer(Base):
    """An answer to a doubt. Can be upvoted, and one can be accepted as solution."""

    __tablename__ = "doubt_answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    doubt_id: Mapped[int] = mapped_column(
        ForeignKey("doubts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    answered_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    is_accepted: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    doubt: Mapped["Doubt"] = relationship(back_populates="answers")
    votes: Mapped[list["AnswerVote"]] = relationship(
        back_populates="answer", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<DoubtAnswer id={self.id} doubt={self.doubt_id} "
            f"accepted={self.is_accepted}>"
        )


class AnswerVote(Base):
    """One upvote on an answer by one user (at most one per answer+user)."""

    __tablename__ = "answer_votes"
    __table_args__ = (
        UniqueConstraint("answer_id", "user_id", name="uq_answer_vote_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    answer_id: Mapped[int] = mapped_column(
        ForeignKey("doubt_answers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    answer: Mapped["DoubtAnswer"] = relationship(back_populates="votes")

    def __repr__(self) -> str:
        return f"<AnswerVote answer={self.answer_id} user={self.user_id}>"


class TimetableEntry(Base):
    """A single recurring weekly class slot in a section's timetable.

    The timetable is modelled as recurring weekly slots (the same schedule
    repeats every week): one row = "Section A, Monday 09:00-10:00, DBMS, taught
    by Prof X, Room 101". `day_of_week` is 0=Monday .. 6=Sunday. A section may
    not have two slots that start at the same time on the same weekday
    (enforced by a unique constraint).
    """

    __tablename__ = "timetable_entries"
    __table_args__ = (
        UniqueConstraint(
            "section_id",
            "day_of_week",
            "start_time",
            name="uq_timetable_section_day_start",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    section_id: Mapped[int] = mapped_column(
        ForeignKey("sections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Optional subject taught in this slot (e.g. 'DBMS').
    subject_id: Mapped[int | None] = mapped_column(
        ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # The teacher who takes this class (optional staff account).
    teacher_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # 0=Monday .. 6=Sunday (kept as an int so the grid sorts naturally).
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    room: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<TimetableEntry id={self.id} section={self.section_id} "
            f"day={self.day_of_week} {self.start_time}-{self.end_time}>"
        )


# --- Leave / OD requests --------------------------------------------------
class LeaveRequestType(str, enum.Enum):
    """Two kinds of planned absence, with different attendance impact.

    leave -> a personal absence (medical / personal / emergency). Counts
             against attendance unless explicitly excused.
    od    -> "on duty": the student is away on OFFICIAL college work (fest,
             hackathon, sports, paper presentation, NSS/NCC, industrial visit,
             placement interview, ...). Approved OD is condoned, so it must NOT
             pull the student's attendance percentage down.
    """

    leave = "leave"
    od = "od"


class LeaveStatus(str, enum.Enum):
    """Lifecycle of a leave/OD request (human-in-the-loop approval)."""

    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"


class LeaveRequest(Base):
    """A student's leave or on-duty (OD) request covering a date range.

    One row = one student's request for [start_date, end_date]. A student raises
    their own request (status `pending`) and a class teacher / mentor / admin
    approves or rejects it.

    Bulk OD: for fests and group events many students go together, so a staff
    coordinator can raise OD for a whole list of students in one shot. Each
    selected student still gets their OWN row (so attendance condonation stays
    per-student), the rows are linked by a shared `bulk_group_id`, and they are
    auto-approved - the staff member raising it IS the approving authority.
    """

    __tablename__ = "leave_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    # leave (personal) vs od (official duty) - drives the attendance impact.
    request_type: Mapped[LeaveRequestType] = mapped_column(
        Enum(LeaveRequestType, name="leave_request_type"),
        nullable=False,
        index=True,
    )
    # Sub-category within the type (e.g. "medical" for leave, "fest" for OD).
    # Kept as a short string (validated in the router) so new event types can be
    # added without a database migration.
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    # The student this request is FOR.
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # The student's section at apply time (denormalised for staff filtering).
    section_id: Mapped[int | None] = mapped_column(
        ForeignKey("sections.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # For OD: the event/competition name (e.g. "TechFest 2026").
    event_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # Optional supporting proof (medical certificate / event invite link).
    proof_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[LeaveStatus] = mapped_column(
        Enum(LeaveStatus, name="leave_status"),
        nullable=False,
        default=LeaveStatus.pending,
        index=True,
    )
    # Who actually created the row (the student, or a staff coordinator for OD).
    applied_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # The staff member who approved/rejected it.
    reviewed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Groups the rows created together by one bulk-OD action (NULL for singles).
    bulk_group_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<LeaveRequest id={self.id} type={self.request_type} "
            f"student={self.student_id} status={self.status}>"
        )


# --- Recruiter portal ------------------------------------------------------
class RecruiterStatus(str, enum.Enum):
    """Lifecycle of a recruiting company in the placement portal."""

    pending = "pending"      # invited, awaiting first HR login
    active = "active"        # at least one HR has accepted & can log in
    suspended = "suspended"  # access revoked by the TPO


class InviteStatus(str, enum.Enum):
    """Lifecycle of a single-use recruiter invitation token."""

    pending = "pending"
    accepted = "accepted"
    revoked = "revoked"
    expired = "expired"


class TenantInvite(Base):
    """A single-use invite an institute admin sends so a user can self-onboard
    into that tenant with a pre-assigned role.

    Mirrors RecruiterInvite: created `pending`, becomes `accepted` once the
    user sets up their account, `expired` past `expires_at`, or `revoked` if
    the admin cancels it. The token is unique and unguessable.
    """

    __tablename__ = "tenant_invites"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    # Role the invited user will get on accept (student/teacher/tpo/admin).
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), nullable=False
    )
    token: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    status: Mapped[InviteStatus] = mapped_column(
        Enum(InviteStatus, name="invite_status"),
        default=InviteStatus.pending,
        nullable=False,
        index=True,
    )
    invited_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<TenantInvite tenant={self.tenant_id} email={self.email!r} "
            f"status={self.status.value}>"
        )


class Recruiter(Base):
    """A recruiting company onboarded by the TPO (one row per company).

    External companies that hire from the institute. The TPO creates the row
    when inviting the company's first HR; it flips to `active` once an invite
    is accepted. All recruiter logins are scoped to exactly one company.
    """

    __tablename__ = "recruiters"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_name: Mapped[str] = mapped_column(
        String(200), nullable=False, index=True
    )
    website: Mapped[str | None] = mapped_column(String(300), nullable=True)
    about: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[RecruiterStatus] = mapped_column(
        Enum(RecruiterStatus, name="recruiter_status"),
        default=RecruiterStatus.pending,
        nullable=False,
        index=True,
    )
    # The TPO/admin who onboarded this company (kept for the audit trail).
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    members: Mapped[list["RecruiterUser"]] = relationship(
        back_populates="recruiter", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<Recruiter id={self.id} company={self.company_name!r} "
            f"status={self.status.value}>"
        )


class RecruiterUser(Base):
    """Links a login account (role=recruiter) to its company (multi-HR ready).

    One account belongs to exactly one company (unique on user_id). `is_primary`
    marks the first/lead HR. Deleting either side cascades this link away.
    """

    __tablename__ = "recruiter_users"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_recruiter_user_account"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    recruiter_id: Mapped[int] = mapped_column(
        ForeignKey("recruiters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # The HR's designation at the company (e.g. "Talent Lead").
    title: Mapped[str | None] = mapped_column(String(150), nullable=True)
    is_primary: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    recruiter: Mapped["Recruiter"] = relationship(back_populates="members")

    def __repr__(self) -> str:
        return (
            f"<RecruiterUser user={self.user_id} "
            f"recruiter={self.recruiter_id} primary={self.is_primary}>"
        )


class RecruiterInvite(Base):
    """A single-use invite token the TPO sends so a recruiter can self-onboard.

    Created `pending`; becomes `accepted` when the recruiter sets up their
    account, `expired` past `expires_at`, or `revoked` if the TPO cancels it.
    The token is unique and unguessable (secrets.token_urlsafe).
    """

    __tablename__ = "recruiter_invites"

    id: Mapped[int] = mapped_column(primary_key=True)
    recruiter_id: Mapped[int] = mapped_column(
        ForeignKey("recruiters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    token: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    status: Mapped[InviteStatus] = mapped_column(
        Enum(InviteStatus, name="invite_status"),
        default=InviteStatus.pending,
        nullable=False,
        index=True,
    )
    # Optional designation to pre-fill on the new HR's account.
    title: Mapped[str | None] = mapped_column(String(150), nullable=True)
    invited_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<RecruiterInvite id={self.id} email={self.email!r} "
            f"status={self.status.value}>"
        )
