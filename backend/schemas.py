"""Pydantic schemas (request/response shapes) for the API.

Validated 'contracts' at the HTTP boundary - separate from the SQLAlchemy ORM
models, which represent database rows.
"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from models import ApplicationStatus, AttendanceStatus, SkillStatus, UserRole


# --- Auth -----------------------------------------------------------------
class UserCreate(BaseModel):
    """Payload for public self-registration."""

    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=6, max_length=128)
    role: UserRole = UserRole.student


class UserOut(BaseModel):
    """Safe, public view of a user (never includes the password hash)."""

    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    section_id: int | None = None  # a student's class/section (None for staff)

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """JWT returned on successful login."""

    access_token: str
    token_type: str = "bearer"


# --- Admin: Users ----------------------------------------------------------
class AdminUserCreate(BaseModel):
    """Admin-created account. Unlike self-signup, role is set deliberately."""

    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=6, max_length=128)
    role: UserRole = UserRole.student


class UserRoleUpdate(BaseModel):
    role: UserRole


class UserStatusUpdate(BaseModel):
    is_active: bool


class UserSectionUpdate(BaseModel):
    """Assign a student to a section (or clear it with section_id=null)."""

    section_id: int | None = None


# --- Admin: Departments ----------------------------------------------------
class DepartmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150, examples=["Computer Science"])
    code: str = Field(min_length=1, max_length=20, examples=["CSE"])


class DepartmentOut(BaseModel):
    id: int
    name: str
    code: str

    model_config = ConfigDict(from_attributes=True)


# --- Admin: Sections -------------------------------------------------------
class SectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50, examples=["A"])
    year: int | None = Field(default=None, ge=1, le=10, examples=[3])


class SectionOut(BaseModel):
    id: int
    name: str
    year: int | None
    department_id: int

    model_config = ConfigDict(from_attributes=True)


# --- Academics: Subjects (teacher-managed curriculum) ----------------------
class SubjectCreate(BaseModel):
    department_id: int = Field(examples=[1])
    name: str = Field(min_length=1, max_length=150, examples=["Database Management Systems"])
    code: str = Field(min_length=1, max_length=30, examples=["CS501"])
    credits: int = Field(ge=1, le=10, examples=[4])
    semester: int = Field(ge=1, le=12, examples=[5])


class SubjectOut(BaseModel):
    id: int
    name: str
    code: str
    credits: int
    semester: int
    department_id: int

    model_config = ConfigDict(from_attributes=True)


# --- Attendance ------------------------------------------------------------
class AttendanceMarkItem(BaseModel):
    """A single student's status within a bulk mark request."""

    student_id: int
    status: AttendanceStatus = AttendanceStatus.present


class AttendanceMarkRequest(BaseModel):
    """Mark (or re-mark) attendance for several students in one section/date."""

    section_id: int
    date: date
    records: list[AttendanceMarkItem] = Field(min_length=1)


class AttendanceRecordOut(BaseModel):
    id: int
    student_id: int
    section_id: int
    date: date
    status: AttendanceStatus

    model_config = ConfigDict(from_attributes=True)


class AttendanceSummaryOut(BaseModel):
    """Aggregated view for a single student."""

    total: int
    present: int
    absent: int
    late: int
    percentage: float  # (present + late) / total * 100


# --- Academics: Results ----------------------------------------------------
class ResultCreate(BaseModel):
    """Teacher enters a student's marks for a subject. Grade point is derived."""

    student_id: int
    subject_id: int
    marks_obtained: float = Field(ge=0, examples=[78])
    max_marks: float = Field(default=100.0, gt=0, examples=[100])


class ResultOut(BaseModel):
    id: int
    student_id: int
    subject_id: int
    marks_obtained: float
    max_marks: float
    grade_point: float

    model_config = ConfigDict(from_attributes=True)


class SemesterGPA(BaseModel):
    """Credit-weighted SGPA for one semester."""

    semester: int
    sgpa: float
    credits: int


class AcademicSummaryOut(BaseModel):
    """A student's CGPA plus a per-semester SGPA breakdown."""

    cgpa: float
    total_credits: int
    semesters: list[SemesterGPA]


# --- Skills (verified data moat) -------------------------------------------
class SkillCreate(BaseModel):
    """A student claims a skill and (optionally) links proof. Starts pending."""

    name: str = Field(min_length=1, max_length=100, examples=["FastAPI"])
    evidence_url: str | None = Field(
        default=None, max_length=500, examples=["https://github.com/me/project"]
    )
    evidence_note: str | None = Field(default=None, max_length=2000)


class SkillOut(BaseModel):
    id: int
    student_id: int
    name: str
    evidence_url: str | None
    evidence_note: str | None
    status: SkillStatus
    ai_score: float | None
    review_note: str | None

    model_config = ConfigDict(from_attributes=True)


class SkillDecision(BaseModel):
    """A mentor's verify/flag decision on a pending skill."""

    status: SkillStatus = Field(examples=["verified"])  # must be verified|flagged
    review_note: str | None = Field(default=None, max_length=500)


# --- Projects (individual or group, verified per member) -------------------
class ProjectMemberInput(BaseModel):
    """A teammate to add on a group project (besides yourself, the owner)."""

    student_id: int
    contribution: str | None = Field(
        default=None, max_length=500, examples=["Built the auth + DB layer"]
    )


class ProjectCreate(BaseModel):
    """Create a project. For a group project, set is_group=true and list members."""

    title: str = Field(min_length=1, max_length=200, examples=["Campus Attendance API"])
    description: str | None = Field(default=None, max_length=4000)
    tech_stack: str | None = Field(
        default=None, max_length=300, examples=["FastAPI, PostgreSQL, Docker"]
    )
    repo_url: str | None = Field(
        default=None, max_length=500, examples=["https://github.com/me/campus-api"]
    )
    demo_url: str | None = Field(default=None, max_length=500)
    is_group: bool = False
    # Teammates besides you. Ignored when is_group is false. You (the creator)
    # are always added automatically as a member.
    members: list[ProjectMemberInput] = Field(default_factory=list)


class ProjectMemberOut(BaseModel):
    id: int
    project_id: int
    student_id: int
    contribution: str | None
    status: SkillStatus
    ai_score: float | None
    review_note: str | None

    model_config = ConfigDict(from_attributes=True)


class ProjectOut(BaseModel):
    id: int
    owner_id: int
    title: str
    description: str | None
    tech_stack: str | None
    repo_url: str | None
    demo_url: str | None
    is_group: bool
    members: list[ProjectMemberOut]

    model_config = ConfigDict(from_attributes=True)


class ProjectMemberDecision(BaseModel):
    """A mentor's verify/flag decision on one member's contribution."""

    status: SkillStatus = Field(examples=["verified"])  # must be verified|flagged
    review_note: str | None = Field(default=None, max_length=500)


class ProjectMemberQueueOut(BaseModel):
    """A pending contribution in the mentor's review queue, with project context."""

    member_id: int
    project_id: int
    project_title: str
    repo_url: str | None
    student_id: int
    contribution: str | None
    status: SkillStatus


# --- Placement: Drives & Eligibility ---------------------------------------
class DriveCreate(BaseModel):
    """TPO posts a drive with its eligibility criteria.

    All criteria are checked against each student's VERIFIED data. Leave a
    criterion at its default (0 / empty) to skip it.
    """

    company_name: str = Field(min_length=1, max_length=200, examples=["Acme Corp"])
    role_title: str = Field(min_length=1, max_length=200, examples=["Backend Engineer"])
    description: str | None = Field(default=None, max_length=4000)
    location: str | None = Field(default=None, max_length=150, examples=["Bangalore"])
    package_lpa: float | None = Field(default=None, ge=0, examples=[12.0])
    min_cgpa: float = Field(default=0.0, ge=0, le=10, examples=[7.0])
    min_attendance: float = Field(default=0.0, ge=0, le=100, examples=[75])
    min_verified_projects: int = Field(default=0, ge=0, examples=[1])
    required_skills: str | None = Field(
        default=None,
        max_length=500,
        examples=["FastAPI, SQL, Docker"],
        description="Comma-separated skill names; matched against verified skills.",
    )
    deadline: date | None = None


class DriveOut(BaseModel):
    id: int
    company_name: str
    role_title: str
    description: str | None
    location: str | None
    package_lpa: float | None
    min_cgpa: float
    min_attendance: float
    min_verified_projects: int
    required_skills: str | None
    is_open: bool
    deadline: date | None

    model_config = ConfigDict(from_attributes=True)


class DriveStatusUpdate(BaseModel):
    """Open or close a drive for the eligibility/application window."""

    is_open: bool


class EligibilityReason(BaseModel):
    """Why one criterion passed or failed (explainable eligibility)."""

    criterion: str
    passed: bool
    detail: str


class StudentEligibilityOut(BaseModel):
    """One student's eligibility verdict for a drive (TPO view)."""

    student_id: int
    full_name: str
    eligible: bool
    cgpa: float
    attendance: float
    verified_skills: int
    verified_projects: int
    reasons: list[EligibilityReason]


class MyEligibilityOut(BaseModel):
    """The logged-in student's own eligibility breakdown for a drive."""

    drive_id: int
    eligible: bool
    cgpa: float
    attendance: float
    verified_skills: int
    verified_projects: int
    reasons: list[EligibilityReason]


# --- Placement: Applications & Shortlisting ---------------------------------
class ApplicationOut(BaseModel):
    """A student's application record."""

    id: int
    drive_id: int
    student_id: int
    status: ApplicationStatus
    note: str | None

    model_config = ConfigDict(from_attributes=True)


class ApplicationStatusUpdate(BaseModel):
    """TPO decision on an application (shortlist / select / reject)."""

    status: ApplicationStatus = Field(examples=["shortlisted"])
    note: str | None = Field(default=None, max_length=500)


class DriveBriefOut(BaseModel):
    """Compact drive view embedded in a student's application list."""

    id: int
    company_name: str
    role_title: str
    package_lpa: float | None
    is_open: bool

    model_config = ConfigDict(from_attributes=True)


class MyApplicationOut(BaseModel):
    """One of the logged-in student's applications, with drive context."""

    id: int
    status: ApplicationStatus
    note: str | None
    drive: DriveBriefOut

    model_config = ConfigDict(from_attributes=True)


class ApplicantOut(BaseModel):
    """An applicant on a drive (TPO view), with a verified-data snapshot."""

    application_id: int
    student_id: int
    full_name: str
    status: ApplicationStatus
    eligible: bool
    cgpa: float
    attendance: float
    verified_skills: int
    verified_projects: int
    note: str | None


# --- Marketing: Leads & Feedback -------------------------------------------
class LeadCreate(BaseModel):
    """Public contact / demo-request submission from the marketing site."""

    name: str = Field(min_length=1, max_length=255, examples=["Asha Mehta"])
    email: EmailStr
    institute: str | None = Field(default=None, max_length=255)
    role: str | None = Field(
        default=None, max_length=100, examples=["Administrator"]
    )
    message: str = Field(min_length=1, max_length=4000)


class LeadOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    institute: str | None
    role: str | None
    message: str
    handled: bool

    model_config = ConfigDict(from_attributes=True)


class FeedbackCreate(BaseModel):
    """Anonymous in-product feedback. Rating is an optional 1-5 score."""

    message: str = Field(min_length=1, max_length=4000)
    category: str | None = Field(default=None, max_length=50, examples=["bug"])
    rating: int | None = Field(default=None, ge=1, le=5, examples=[5])


class FeedbackOut(BaseModel):
    id: int
    category: str | None
    rating: int | None
    message: str

    model_config = ConfigDict(from_attributes=True)


# --- Announcements ---------------------------------------------------------
class AnnouncementCreate(BaseModel):
    """Admin posts an announcement to everyone or to a single role."""

    title: str = Field(min_length=1, max_length=200, examples=["Mid-sem exams"])
    body: str = Field(min_length=1, max_length=5000)
    audience: Literal["all", "student", "teacher", "tpo"] = "all"


class AnnouncementOut(BaseModel):
    id: int
    title: str
    body: str
    audience: str
    author_id: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Academic Calendar -----------------------------------------------------
class CalendarEventCreate(BaseModel):
    """Admin adds an academic-calendar entry (holiday/exam/event/deadline)."""

    title: str = Field(
        min_length=1, max_length=200, examples=["Semester exams begin"]
    )
    description: str | None = Field(default=None, max_length=2000)
    event_date: date
    end_date: date | None = None
    category: Literal["holiday", "exam", "event", "deadline"] = "event"
    audience: Literal["all", "student", "teacher", "tpo"] = "all"


class CalendarEventOut(BaseModel):
    id: int
    title: str
    description: str | None
    event_date: date
    end_date: date | None
    category: str
    audience: str
    created_by_id: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Audit Log -------------------------------------------------------------
class AuditLogOut(BaseModel):
    id: int
    actor_id: int | None
    actor_email: str | None
    action: str
    target_type: str | None
    target_id: str | None
    summary: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
