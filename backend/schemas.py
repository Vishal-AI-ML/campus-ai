"""Pydantic schemas (request/response shapes) for the API.

Validated 'contracts' at the HTTP boundary - separate from the SQLAlchemy ORM
models, which represent database rows.
"""

from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from models import (
    ApplicationStatus,
    AttendanceStatus,
    DoubtStatus,
    ECACategory,
    InviteStatus,
    LeaveRequestType,
    LeaveStatus,
    MaterialCategory,
    OfferStatus,
    RecruiterDecision,
    RecruiterStatus,
    SkillStatus,
    SubmissionStatus,
    UserRole,
)


# --- Auth -----------------------------------------------------------------
class UserCreate(BaseModel):
    """Payload for public self-registration.

    SECURITY: self-registration ALWAYS creates a `student` account. Staff roles
    (teacher/tpo/admin) and recruiters are provisioned only by an admin (or via
    the recruiter invite flow) - never by this public endpoint. The `role` field
    is intentionally NOT accepted here so it cannot be elevated by the caller.
    """

    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=6, max_length=128)


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
    # True when an `absent` record falls inside an approved leave/OD and is
    # therefore excused (does not count against the student's percentage).
    condoned: bool = False
    # Short human reason, e.g. "OD: Spring Fest" or "Leave: medical".
    condone_reason: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AttendanceSummaryOut(BaseModel):
    """Aggregated view for a single student.

    Absences covered by an approved leave/OD are condoned: counted as `excused`
    and removed from the percentage denominator. `raw_percentage` keeps the
    pre-condonation value for transparency.
    """

    total: int
    present: int
    absent: int  # absences that are NOT condoned
    late: int
    excused: int = 0  # condoned absences (approved OD / leave)
    percentage: float  # condoned: (present + late) / (total - excused) * 100
    raw_percentage: float = 0.0  # before condonation: (present + late) / total * 100


# --- Face attendance / enrollment ------------------------------------------
class FaceEnrollRequest(BaseModel):
    """Enroll (or re-enroll) a student's reference face from a base64 photo."""

    student_id: int = Field(gt=0)
    image_base64: str = Field(min_length=1)


class FaceEnrollmentOut(BaseModel):
    """A stored enrollment record (the embedding itself lives in Qdrant)."""

    student_id: int
    enrolled_by_id: int | None
    det_score: float | None
    enrolled_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FaceEnrollmentStatusOut(BaseModel):
    """A roster student + whether they have an enrolled reference face."""

    student_id: int
    full_name: str
    email: EmailStr
    enrolled: bool
    det_score: float | None = None
    enrolled_at: datetime | None = None


class FacePhotoMatchRequest(BaseModel):
    """Match a class photo against a section's enrolled students."""

    section_id: int = Field(gt=0)
    image_base64: str = Field(min_length=1)
    score_threshold: float | None = Field(default=None, ge=0.0, le=1.0)


class FaceMatchSuggestion(BaseModel):
    """One roster student + whether the class photo matched them."""

    student_id: int
    full_name: str
    enrolled: bool
    matched: bool
    score: float | None = None
    suggested_status: AttendanceStatus


class FaceMatchOutsider(BaseModel):
    """An enrolled student matched in the photo but NOT in this section."""

    student_id: int
    score: float


class FacePhotoMatchResponse(BaseModel):
    """Suggested attendance from a class photo (teacher confirms before marking)."""

    section_id: int
    detected_faces: int
    unmatched_faces: int
    threshold: float
    suggestions: list[FaceMatchSuggestion]
    matched_outside_section: list[FaceMatchOutsider]


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


# --- Extra-curricular activities (ECA - verified data moat) ----------------
class ECACreate(BaseModel):
    """A student logs an extra-curricular activity + optional proof. Starts pending."""

    title: str = Field(
        min_length=1, max_length=150, examples=["Inter-college Football Captain"]
    )
    category: ECACategory = Field(default=ECACategory.other, examples=["sports"])
    organization: str | None = Field(
        default=None, max_length=150, examples=["Sports Committee"]
    )
    description: str | None = Field(default=None, max_length=2000)
    evidence_url: str | None = Field(
        default=None, max_length=500, examples=["https://example.com/certificate.pdf"]
    )


class ECAOut(BaseModel):
    id: int
    student_id: int
    title: str
    category: ECACategory
    organization: str | None
    description: str | None
    evidence_url: str | None
    status: SkillStatus
    review_note: str | None

    model_config = ConfigDict(from_attributes=True)


class ECADecision(BaseModel):
    """A teacher/TPO's verify/flag decision on a pending ECA claim."""

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
    recruiter_id: int | None = None

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
    # Whether the TPO has revealed this candidate's contact to the recruiter.
    contact_revealed: bool = False


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


# --- Assignments -----------------------------------------------------------
class AssignmentCreate(BaseModel):
    """Teacher posts an assignment for a section (optionally tied to a subject)."""

    section_id: int = Field(gt=0)
    subject_id: int | None = Field(default=None, gt=0)
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    due_date: datetime
    max_marks: float = Field(default=100.0, gt=0)


class AssignmentOut(BaseModel):
    id: int
    section_id: int
    subject_id: int | None
    title: str
    description: str | None
    due_date: datetime
    max_marks: float
    created_by_id: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssignmentWithStatusOut(AssignmentOut):
    """An assignment + the logged-in student's own submission state."""

    submitted: bool = False
    submission_status: SubmissionStatus | None = None
    marks: float | None = None


class SubmissionCreate(BaseModel):
    """A student turns in work: free text and/or a link (at least one)."""

    content: str | None = Field(default=None, max_length=10000)
    link: str | None = Field(default=None, max_length=500)


class SubmissionGrade(BaseModel):
    """A teacher grades a submission (marks must be within the assignment max)."""

    marks: float = Field(ge=0)
    feedback: str | None = Field(default=None, max_length=2000)


class SubmissionOut(BaseModel):
    id: int
    assignment_id: int
    student_id: int
    content: str | None
    link: str | None
    status: SubmissionStatus
    marks: float | None
    feedback: str | None
    graded_by_id: int | None
    submitted_at: datetime
    graded_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


# --- Study Hub: Materials --------------------------------------------------
class MaterialCreate(BaseModel):
    """Teacher/admin uploads a study material for a section.

    Provide inline `content` (notes text) and/or an external `link` - at least
    one is required (validated in the router).
    """

    section_id: int = Field(gt=0, examples=[1])
    subject_id: int | None = Field(default=None, gt=0, examples=[1])
    title: str = Field(
        min_length=1, max_length=200, examples=["Unit 1 - ER Models"]
    )
    description: str | None = Field(default=None, max_length=2000)
    content: str | None = Field(default=None, max_length=20000)
    link: str | None = Field(
        default=None,
        max_length=500,
        examples=["https://drive.google.com/notes"],
    )
    category: MaterialCategory = MaterialCategory.notes


class MaterialOut(BaseModel):
    """A study material as returned to staff and students."""

    id: int
    section_id: int
    subject_id: int | None
    title: str
    description: str | None
    content: str | None
    link: str | None
    category: MaterialCategory
    uploaded_by_id: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Doubt Forum -----------------------------------------------------------
class DoubtCreate(BaseModel):
    """A student/staff posts a question to a section's doubt forum."""

    section_id: int = Field(gt=0, examples=[1])
    subject_id: int | None = Field(default=None, gt=0, examples=[1])
    title: str = Field(
        min_length=1, max_length=200, examples=["Doubt in normalization"]
    )
    body: str = Field(min_length=1, max_length=5000)


class AnswerCreate(BaseModel):
    """An answer to a doubt."""

    body: str = Field(min_length=1, max_length=5000)


class AnswerOut(BaseModel):
    """An answer with its live upvote count + whether the viewer upvoted it."""

    id: int
    doubt_id: int
    body: str
    answered_by_id: int | None
    is_accepted: bool
    upvote_count: int
    viewer_has_upvoted: bool
    created_at: datetime


class DoubtOut(BaseModel):
    """A doubt list item, with a live answer count."""

    id: int
    section_id: int
    subject_id: int | None
    title: str
    body: str
    status: DoubtStatus
    asked_by_id: int | None
    answer_count: int
    created_at: datetime
    resolved_at: datetime | None


class DoubtDetailOut(DoubtOut):
    """A doubt plus all of its answers (accepted first, then most upvoted)."""

    answers: list[AnswerOut]


# --- Timetable (weekly recurring class schedule) ---------------------------
class TimetableEntryCreate(BaseModel):
    """Create a recurring weekly class slot for a section (staff only)."""

    section_id: int = Field(gt=0)
    subject_id: int | None = Field(default=None, gt=0)
    teacher_id: int | None = Field(default=None, gt=0)
    day_of_week: int = Field(ge=0, le=6, examples=[0])  # 0=Mon .. 6=Sun
    start_time: time = Field(examples=["09:00"])
    end_time: time = Field(examples=["10:00"])
    room: str | None = Field(default=None, max_length=100, examples=["Room 101"])


class TimetableEntryUpdate(BaseModel):
    """Patch an existing slot. Only the fields you send are changed.

    (`section_id` is intentionally immutable - delete + recreate to move a slot
    to another section.)
    """

    subject_id: int | None = Field(default=None, gt=0)
    teacher_id: int | None = Field(default=None, gt=0)
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    start_time: time | None = None
    end_time: time | None = None
    room: str | None = Field(default=None, max_length=100)


class TimetableEntryOut(BaseModel):
    """A timetable slot enriched with section/subject/teacher display names."""

    id: int
    section_id: int
    section_name: str | None = None
    subject_id: int | None = None
    subject_name: str | None = None
    teacher_id: int | None = None
    teacher_name: str | None = None
    day_of_week: int
    start_time: time
    end_time: time
    room: str | None = None


# --- Leave / OD -----------------------------------------------------------
class LeaveRequestCreate(BaseModel):
    """A user applies for their OWN leave or OD for a date range.

    `category` is validated in the router against the set allowed for the chosen
    `request_type` (medical/personal/emergency for leave; fest/technical/sports/
    competition/ncc_nss/industrial_visit/placement/other for OD).
    """

    request_type: LeaveRequestType
    category: str = Field(min_length=1, max_length=50, examples=["medical"])
    title: str = Field(min_length=1, max_length=200, examples=["Fever - need rest"])
    reason: str | None = Field(default=None, max_length=2000)
    event_name: str | None = Field(default=None, max_length=200)
    proof_url: str | None = Field(default=None, max_length=500)
    start_date: date
    end_date: date


class BulkODCreate(BaseModel):
    """Staff raises ON-DUTY for many students at once for a single event.

    Each student gets their own auto-approved OD row, linked by a shared bulk
    group id. Used for fests / sports / group events.
    """

    student_ids: list[int] = Field(min_length=1, examples=[[6, 7, 8]])
    category: str = Field(min_length=1, max_length=50, examples=["fest"])
    title: str = Field(min_length=1, max_length=200, examples=["TechFest 2026"])
    event_name: str | None = Field(default=None, max_length=200)
    reason: str | None = Field(default=None, max_length=2000)
    proof_url: str | None = Field(default=None, max_length=500)
    start_date: date
    end_date: date


class LeaveDecision(BaseModel):
    """A staff approve/reject decision on a pending request."""

    status: Literal["approved", "rejected"]
    review_note: str | None = Field(default=None, max_length=2000)


class LeaveRequestOut(BaseModel):
    """A leave/OD request enriched with student / section / reviewer names."""

    id: int
    request_type: LeaveRequestType
    category: str
    student_id: int
    student_name: str | None = None
    section_id: int | None = None
    section_name: str | None = None
    title: str
    reason: str | None = None
    event_name: str | None = None
    proof_url: str | None = None
    start_date: date
    end_date: date
    status: LeaveStatus
    applied_by_id: int | None = None
    reviewed_by_id: int | None = None
    reviewer_name: str | None = None
    review_note: str | None = None
    reviewed_at: datetime | None = None
    bulk_group_id: str | None = None
    days: int = 1
    created_at: datetime


class BulkODResult(BaseModel):
    """Summary returned after a bulk-OD action."""

    bulk_group_id: str
    created: int
    skipped: list[int] = []
    entries: list[LeaveRequestOut] = []


# --- Analytics / At-risk --------------------------------------------------
class RiskFactorOut(BaseModel):
    """One explainable contributor to a student's risk score."""

    key: str
    label: str
    value: float | None = None
    risk: float | None = None
    weight: float
    available: bool


class StudentRiskOut(BaseModel):
    """A student's at-risk assessment with a transparent factor breakdown."""

    student_id: int
    student_name: str | None = None
    risk_score: float
    band: str  # high | medium | low
    attendance_pct: float | None = None
    cgpa: float | None = None
    submission_rate: float | None = None
    reasons: list[str] = []
    factors: list[RiskFactorOut] = []


class ClassAnalyticsOut(BaseModel):
    """Aggregate analytics for one section (teacher dashboard)."""

    section_id: int
    section_name: str | None = None
    student_count: int
    avg_attendance_pct: float | None = None
    avg_cgpa: float | None = None
    results_coverage: int = 0
    total_assignments: int = 0
    avg_submission_rate: float | None = None
    risk_high: int = 0
    risk_medium: int = 0
    risk_low: int = 0
    at_risk_count: int = 0


# --- Placement analytics (TPO dashboard) -----------------------------------
class PlacementFunnelOut(BaseModel):
    """Current status distribution across all applications."""

    applied: int = 0
    shortlisted: int = 0
    selected: int = 0
    rejected: int = 0


class DrivePerformanceOut(BaseModel):
    """Per-drive recruitment performance snapshot."""

    drive_id: int
    company_name: str
    role_title: str
    package_lpa: float | None = None
    is_open: bool
    applicants: int = 0
    shortlisted: int = 0
    selected: int = 0
    rejected: int = 0
    selection_rate: float | None = None


class CompanyStatOut(BaseModel):
    """Aggregated outcomes for one company across its drives."""

    company_name: str
    drives: int = 0
    applicants: int = 0
    selected: int = 0
    avg_package: float | None = None


class PlacementAnalyticsOut(BaseModel):
    """Whole-program placement analytics for the TPO dashboard."""

    total_drives: int = 0
    open_drives: int = 0
    closed_drives: int = 0
    total_applications: int = 0
    unique_applicants: int = 0
    placed_students: int = 0
    total_active_students: int = 0
    placement_rate: float | None = None
    applicant_conversion: float | None = None
    avg_package: float | None = None
    highest_package: float | None = None
    highest_package_company: str | None = None
    funnel: PlacementFunnelOut
    drives: list[DrivePerformanceOut] = []
    companies: list[CompanyStatOut] = []


# --- Admin: bulk user import ----------------------------------------------
class BulkImportRowResult(BaseModel):
    """Outcome of importing a single CSV row."""

    row: int
    email: str | None = None
    status: Literal["created", "skipped"]
    detail: str
    user_id: int | None = None
    role: UserRole | None = None
    temp_password: str | None = None  # set only when auto-generated


class BulkImportResult(BaseModel):
    """Summary of a bulk user-import run."""

    total_rows: int
    created: int
    skipped: int
    results: list[BulkImportRowResult]


# --- Recruiter portal ------------------------------------------------------
class RecruiterInviteCreate(BaseModel):
    """TPO payload: onboard a company and invite its first HR."""

    company_name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    website: str | None = Field(default=None, max_length=300)
    about: str | None = None
    title: str | None = Field(default=None, max_length=150)
    expires_in_days: int = Field(default=14, ge=1, le=90)


class RecruiterOut(BaseModel):
    """Public view of a recruiting company."""

    id: int
    company_name: str
    website: str | None = None
    about: str | None = None
    status: RecruiterStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecruiterInviteOut(BaseModel):
    """Public view of a recruiter invite (never exposes the raw token)."""

    id: int
    recruiter_id: int
    email: EmailStr
    status: InviteStatus
    title: str | None = None
    expires_at: datetime
    accepted_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecruiterInviteCreated(BaseModel):
    """Returned right after creating an invite (includes the one-time token)."""

    invite: RecruiterInviteOut
    recruiter: RecruiterOut
    token: str
    accept_path: str


class RecruiterAcceptInvite(BaseModel):
    """Payload a recruiter submits to accept an invite & create their account."""

    token: str = Field(min_length=10, max_length=64)
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=6, max_length=128)


class RecruiterMeOut(BaseModel):
    """A recruiter's own profile: their account + their company."""

    user: UserOut
    recruiter: RecruiterOut
    title: str | None = None
    is_primary: bool


# --- Recruiter portal: candidate viewing (Step 27.2) -----------------------
class RecruiterDriveOut(BaseModel):
    """A drive linked to the recruiter's company (recruiter view)."""

    id: int
    company_name: str
    role_title: str
    location: str | None = None
    package_lpa: float | None = None
    is_open: bool
    deadline: date | None = None
    shortlisted_count: int
    selected_count: int


class RecruiterCandidateOut(BaseModel):
    """A shortlisted/selected candidate as seen by a recruiter.

    The verified-data snapshot is always visible (the moat's value); contact
    (email) appears only after the TPO reveals it for this application.
    """

    application_id: int
    drive_id: int
    drive_role: str
    status: ApplicationStatus
    full_name: str
    cgpa: float
    attendance: float
    verified_skills: list[str]
    verified_projects: int
    contact_revealed: bool
    email: str | None = None
    # Recruiter's own (non-binding) call on this candidate (Step 27.3).
    recruiter_decision: RecruiterDecision = RecruiterDecision.pending
    recruiter_decision_note: str | None = None
    # Whether this candidate already has a live offer (extended/accepted).
    has_active_offer: bool = False


class RecruiterDecisionUpdate(BaseModel):
    """Recruiter records a non-binding call on a visible candidate (27.3).

    `pending` is not allowed here - use interested / on_hold / rejected.
    """

    decision: RecruiterDecision = Field(examples=["interested"])
    note: str | None = Field(default=None, max_length=500)


class OfferCreate(BaseModel):
    """Recruiter extends an offer to a candidate (Step 27.3).

    `role_title`, `package_lpa` and `location` default to the drive's values
    when omitted, so a quick offer just needs the application id.
    """

    application_id: int = Field(gt=0)
    role_title: str | None = Field(default=None, max_length=200)
    package_lpa: float | None = Field(default=None, ge=0, examples=[8.5])
    location: str | None = Field(default=None, max_length=150)
    joining_date: date | None = None
    expires_on: date | None = None
    note: str | None = Field(default=None, max_length=1000)


class OfferRespond(BaseModel):
    """Student's response to an offer: accept or decline (Step 27.3)."""

    accept: bool
    note: str | None = Field(default=None, max_length=500)


class OfferOut(BaseModel):
    """A full offer record, enriched with drive/company/student context."""

    id: int
    application_id: int
    drive_id: int
    drive_role: str
    company_name: str
    student_id: int
    student_name: str
    role_title: str
    package_lpa: float | None = None
    location: str | None = None
    joining_date: date | None = None
    expires_on: date | None = None
    status: OfferStatus
    note: str | None = None
    student_response_note: str | None = None
    created_at: datetime
    responded_at: datetime | None = None


class DriveRecruiterLink(BaseModel):
    """TPO payload to link (or unlink) a drive to a recruiting company."""

    recruiter_id: int | None = Field(
        default=None, description="Company id to link; null to unlink."
    )


class ContactRevealUpdate(BaseModel):
    """TPO toggle to reveal/hide a candidate's contact to the recruiter."""

    revealed: bool
