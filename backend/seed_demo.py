"""Seed a self-contained DEMO INSTITUTE tenant for browser demos / sandbox.

Why this exists (§7 "seed script for demo sandbox"):
  Spinning up a believable end-to-end demo by hand (institute -> users ->
  departments -> skills -> results -> attendance -> drives -> applications) is
  slow and error-prone. This script does it in one shot, and is **idempotent**
  (safe to re-run — it get-or-creates everything), so the demo data is always
  in a known-good state.

Multi-tenancy safety:
  Everything is created under its OWN tenant (slug ``demo``), completely
  isolated from the real ``default`` institute by the same Postgres RLS that
  protects production. It never touches another tenant's rows.

How it talks to the DB (RLS-aware):
  Prefers ``MIGRATION_DATABASE_URL`` (the postgres OWNER role, which bypasses
  RLS — same connection migrations use) so seeding is friction-free; falls back
  to ``DATABASE_URL`` (the ``app_user`` NOBYPASSRLS role). Either way it sets
  the per-session tenant GUC after creating the tenant and does ALL work in a
  SINGLE transaction (one connection), so FORCE-RLS ``WITH CHECK`` is satisfied
  and the GUC never gets lost to connection pooling.

Run it from the backend folder:
    uv run python seed_demo.py

Then log in (frontend or /docs) with any account below, password: DemoPass123
    admin@demo.campus.ai   (admin)
    teacher@demo.campus.ai (teacher)
    tpo@demo.campus.ai     (tpo)
    aarav@demo.campus.ai   (student)  + diya / kabir / isha / vivaan
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from config import settings
from db import set_current_tenant
from models import (
    Application,
    ApplicationStatus,
    AttendanceRecord,
    AttendanceStatus,
    Department,
    Drive,
    Project,
    ProjectMember,
    Result,
    Section,
    Skill,
    SkillStatus,
    Subject,
    Tenant,
    User,
    UserRole,
)
from security import hash_password

DEMO_SLUG = "demo"
DEMO_PASSWORD = "DemoPass123"


# --- grade slab (mirrors academics.grade_point_for so CGPA matches the app) --
def grade_point_for(percentage: float) -> float:
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
    return 0.0


def get_or_create(db: Session, model, defaults: dict | None = None, **filters):
    """Return (obj, created). Looks up by ``filters``; creates with
    ``filters + defaults`` if missing. Flushes so the new id is available."""
    obj = db.scalar(select(model).filter_by(**filters))
    if obj is not None:
        return obj, False
    obj = model(**{**filters, **(defaults or {})})
    db.add(obj)
    db.flush()
    return obj, True


def _recent_weekdays(n: int) -> list[date]:
    """The last ``n`` weekdays (Mon-Fri), oldest first, ending today-ish."""
    out: list[date] = []
    d = date.today()
    while len(out) < n:
        if d.weekday() < 5:  # 0=Mon .. 4=Fri
            out.append(d)
        d -= timedelta(days=1)
    return list(reversed(out))


def seed(db: Session) -> dict[str, int]:
    now = datetime.now(timezone.utc)
    pw = hash_password(DEMO_PASSWORD)  # hash once, reuse for all demo accounts
    counts: dict[str, int] = {}

    def bump(key: str, created: bool) -> None:
        if created:
            counts[key] = counts.get(key, 0) + 1

    # 1) Tenant (NOT rls-protected) ----------------------------------------
    tenant, c = get_or_create(
        db, Tenant, defaults={"name": "Demo Institute", "is_active": True},
        slug=DEMO_SLUG,
    )
    bump("tenants", c)
    # From here on, stamp the session so every rls-protected insert/read is
    # scoped to (and allowed for) this tenant.
    set_current_tenant(db, tenant.id)
    tid = tenant.id

    # 2) Departments + sections --------------------------------------------
    cse, c = get_or_create(
        db, Department, defaults={"name": "Computer Science"},
        tenant_id=tid, code="CSE",
    )
    bump("departments", c)
    ece, c = get_or_create(
        db, Department, defaults={"name": "Electronics"},
        tenant_id=tid, code="ECE",
    )
    bump("departments", c)

    cse_a, c = get_or_create(
        db, Section, defaults={"tenant_id": tid, "year": 3},
        department_id=cse.id, name="A",
    )
    bump("sections", c)
    ece_a, c = get_or_create(
        db, Section, defaults={"tenant_id": tid, "year": 2},
        department_id=ece.id, name="A",
    )
    bump("sections", c)

    # 3) Subjects (CSE, semester 5) ----------------------------------------
    subj_specs = [
        ("Database Management Systems", "CS501", 4, 5),
        ("Operating Systems", "CS502", 4, 5),
        ("Computer Networks", "CS503", 3, 5),
    ]
    subjects: list[Subject] = []
    for name, code, credits, sem in subj_specs:
        s, c = get_or_create(
            db, Subject,
            defaults={"tenant_id": tid, "name": name, "credits": credits, "semester": sem},
            department_id=cse.id, code=code,
        )
        bump("subjects", c)
        subjects.append(s)

    # 4) Staff accounts -----------------------------------------------------
    def make_user(email, full_name, role, section_id=None):
        u, created = get_or_create(
            db, User,
            defaults={
                "full_name": full_name,
                "hashed_password": pw,
                "role": role,
                "is_active": True,
                "section_id": section_id,
                "tenant_id": tid,
            },
            email=email,
        )
        bump("users", created)
        return u

    make_user("admin@demo.campus.ai", "Demo Admin", UserRole.admin)
    teacher = make_user("teacher@demo.campus.ai", "Prof Anita Rao", UserRole.teacher)
    make_user("tpo@demo.campus.ai", "TPO Rakesh Kumar", UserRole.tpo)

    # 5) Students (CSE-A) ---------------------------------------------------
    student_specs = [
        ("aarav@demo.campus.ai", "Aarav Sharma"),
        ("diya@demo.campus.ai", "Diya Patel"),
        ("kabir@demo.campus.ai", "Kabir Singh"),
        ("isha@demo.campus.ai", "Isha Gupta"),
        ("vivaan@demo.campus.ai", "Vivaan Reddy"),
    ]
    students: list[User] = []
    for email, name in student_specs:
        students.append(make_user(email, name, UserRole.student, section_id=cse_a.id))
    aarav, diya, kabir, isha, vivaan = students

    # 6) Skills (verified + pending) ---------------------------------------
    def make_skill(student, name, status, ai_score=None, note=None):
        defaults = {
            "tenant_id": tid,
            "evidence_url": "https://github.com/demo/proof",
            "evidence_note": note or f"Proof of {name} proficiency.",
            "status": status,
            "ai_score": ai_score,
        }
        if status == SkillStatus.verified:
            defaults["reviewed_by_id"] = teacher.id
            defaults["reviewed_at"] = now
            defaults["review_note"] = "Proof checked — looks genuine."
        s, c = get_or_create(
            db, Skill, defaults=defaults, student_id=student.id, name=name
        )
        bump("skills", c)
        return s

    make_skill(aarav, "Python", SkillStatus.verified, ai_score=92.0)
    make_skill(aarav, "React", SkillStatus.pending)
    make_skill(diya, "Java", SkillStatus.verified, ai_score=88.0)
    make_skill(diya, "Machine Learning", SkillStatus.verified, ai_score=85.0)
    make_skill(kabir, "C++", SkillStatus.pending)
    make_skill(isha, "Python", SkillStatus.verified, ai_score=90.0)
    make_skill(vivaan, "SQL", SkillStatus.pending)

    # 7) Projects (+ per-member verification) ------------------------------
    def make_project(owner, title, is_group, members):
        p, c = get_or_create(
            db, Project,
            defaults={
                "tenant_id": tid,
                "description": f"{title} — a demo project.",
                "tech_stack": "FastAPI, PostgreSQL, React",
                "repo_url": "https://github.com/demo/" + title.lower().replace(" ", "-"),
                "is_group": is_group,
            },
            owner_id=owner.id, title=title,
        )
        bump("projects", c)
        for student, contribution, status in members:
            defaults = {
                "tenant_id": tid,
                "contribution": contribution,
                "status": status,
            }
            if status == SkillStatus.verified:
                defaults["reviewed_by_id"] = teacher.id
                defaults["review_note"] = "Contribution verified."
            _, mc = get_or_create(
                db, ProjectMember, defaults=defaults,
                project_id=p.id, student_id=student.id,
            )
            bump("project_members", mc)
        return p

    make_project(
        aarav, "Campus Connect", True,
        [
            (aarav, "Backend APIs + auth", SkillStatus.verified),
            (diya, "ML recommendation module", SkillStatus.verified),
        ],
    )
    make_project(
        kabir, "IoT Weather Station", False,
        [(kabir, "Full build", SkillStatus.pending)],
    )

    # 8) Results (drives CGPA + at-risk analytics) -------------------------
    # marks per student per subject (DBMS, OS, CN) — strong vs weak mix.
    marks_by_student = {
        aarav.id: [88, 82, 79],
        diya.id: [91, 85, 88],
        kabir.id: [44, 38, 52],   # weak -> low CGPA, at-risk
        isha.id: [76, 71, 68],
        vivaan.id: [63, 59, 66],
    }
    for student in students:
        for subj, marks in zip(subjects, marks_by_student[student.id]):
            pct = marks / 100.0 * 100
            _, c = get_or_create(
                db, Result,
                defaults={
                    "tenant_id": tid,
                    "marks_obtained": float(marks),
                    "max_marks": 100.0,
                    "grade_point": grade_point_for(pct),
                },
                student_id=student.id, subject_id=subj.id,
            )
            bump("results", c)

    # 9) Attendance (last 12 weekdays) -------------------------------------
    # Kabir gets several absents (at-risk), vivaan a few lates, rest mostly present.
    days = _recent_weekdays(12)
    absent_idx = {kabir.id: {1, 3, 5, 7, 9}, isha.id: {4}}
    late_idx = {vivaan.id: {2, 6}, kabir.id: {2}}
    for student in students:
        for i, d in enumerate(days):
            if i in absent_idx.get(student.id, set()):
                st = AttendanceStatus.absent
            elif i in late_idx.get(student.id, set()):
                st = AttendanceStatus.late
            else:
                st = AttendanceStatus.present
            _, c = get_or_create(
                db, AttendanceRecord,
                defaults={
                    "tenant_id": tid,
                    "status": st,
                    "marked_by_id": teacher.id,
                },
                student_id=student.id, section_id=cse_a.id, date=d,
            )
            bump("attendance_records", c)

    # 10) Drives + applications (placement pipeline + analytics) -----------
    tpo = db.scalar(select(User).filter_by(email="tpo@demo.campus.ai"))
    deadline = date.today() + timedelta(days=21)
    acme, c = get_or_create(
        db, Drive,
        defaults={
            "tenant_id": tid,
            "description": "Backend SDE role, great team.",
            "location": "Bengaluru",
            "package_lpa": 12.0,
            "min_cgpa": 7.0,
            "min_attendance": 75.0,
            "min_verified_projects": 1,
            "required_skills": "Python",
            "is_open": True,
            "deadline": deadline,
            "created_by_id": tpo.id,
        },
        company_name="Acme Corp", role_title="Software Engineer",
    )
    bump("drives", c)
    globex, c = get_or_create(
        db, Drive,
        defaults={
            "tenant_id": tid,
            "description": "Entry-level analytics role.",
            "location": "Pune",
            "package_lpa": 8.0,
            "min_cgpa": 6.0,
            "min_attendance": 0.0,
            "min_verified_projects": 0,
            "required_skills": "SQL",
            "is_open": True,
            "deadline": deadline,
            "created_by_id": tpo.id,
        },
        company_name="Globex", role_title="Data Analyst",
    )
    bump("drives", c)

    def make_application(drive, student, status):
        defaults = {
            "tenant_id": tid,
            "status": status,
            "decided_by_id": tpo.id if status != ApplicationStatus.applied else None,
        }
        _, c = get_or_create(
            db, Application, defaults=defaults,
            drive_id=drive.id, student_id=student.id,
        )
        bump("applications", c)

    make_application(acme, aarav, ApplicationStatus.selected)
    make_application(acme, diya, ApplicationStatus.shortlisted)
    make_application(globex, isha, ApplicationStatus.applied)
    make_application(globex, vivaan, ApplicationStatus.applied)

    return counts


def main() -> None:
    # Prefer the owner connection (bypasses RLS, like migrations); fall back to
    # the app_user runtime URL. NullPool + single transaction keeps the tenant
    # GUC stable on one physical connection.
    url = settings.MIGRATION_DATABASE_URL or settings.DATABASE_URL
    role = "owner (MIGRATION_DATABASE_URL)" if settings.MIGRATION_DATABASE_URL else "app_user (DATABASE_URL)"
    engine = create_engine(url, pool_pre_ping=True, future=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, future=True)

    print(f"Seeding Demo Institute via {role} ...")
    db = SessionLocal()
    try:
        counts = seed(db)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    if counts:
        print("Created new rows:")
        for k in sorted(counts):
            print(f"  {k:20s} +{counts[k]}")
    else:
        print("Nothing new — demo data already present (idempotent re-run).")
    print("\nDemo Institute ready. Log in (password: DemoPass123):")
    print("  admin@demo.campus.ai / teacher@demo.campus.ai / tpo@demo.campus.ai")
    print("  students: aarav@ / diya@ / kabir@ / isha@ / vivaan@ demo.campus.ai")


if __name__ == "__main__":
    main()
