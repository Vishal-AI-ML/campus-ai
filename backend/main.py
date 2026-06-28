"""Campus AI - Backend API entrypoint.

Progress:
  * Step 2: config, Supabase Postgres, users + JWT auth.
  * Step 3: Admin - users, departments, sections (RBAC).
  * Attendance: mark/view attendance (teacher marks, students view).
  * Academics: subjects + results + SGPA/CGPA (teacher manages, students view).
  * Skills: claim -> mentor verify/flag (the verified-data moat).
  * Projects: individual/group projects, verified per member.
  * AI auto-scoring of skills/projects via the AI worker (BackgroundTask).
  * AI Career Mentor: grounded chat over the student's verified profile.
  * AI Resume: build a Markdown resume from verified data + ATS score vs a JD.
  * Placement: drives + verified-data eligibility engine.
  * Placement applications: students apply to eligible drives; TPO shortlists.
  * Announcements: admin broadcasts; users read their own role's feed.
  * Academic calendar: admin posts holidays/exams/events; users see their feed.
  * Audit log: append-only trail of admin governance actions.
  * Face attendance: enroll students' reference faces (worker + Qdrant);
    class-photo matching comes next.
  * Assignments: teachers post assignments per section; students submit; teachers grade.
  * Study Hub: teachers upload study materials/notes per section; students browse.
  * Doubt Forum: students post doubts per section; peers/staff answer, upvote & accept.
  * Leave/OD: students apply for leave/on-duty; staff approve; bulk OD for events.
  * Attendance condonation: approved leave/OD excuses matching absences so a
    student's attendance % is never pulled down by official duty/approved leave.
  * Analytics & at-risk: explainable per-student risk (attendance + CGPA +
    submissions) + section dashboards for teachers.

Location:
    E:\\campus-ai\\backend\\main.py

Run (from the backend folder):
    uv run uvicorn main:app --reload --port 8000

Key URLs:
    /docs          -> Swagger UI (test everything here)
    /health        -> liveness probe
    /db-check      -> verifies the database connection
    /auth/*        -> register / login / me
    /admin/*       -> users, departments & sections
    /attendance/*  -> mark & view attendance + class-photo face match
    /academics/*   -> subjects, results & SGPA/CGPA
    /assignments/* -> create, submit & grade assignments
    /materials/*   -> study hub: upload & browse study materials (section-scoped)
    /doubts/*      -> doubt forum: ask, answer, upvote & accept (section-scoped)
    /timetable/*   -> class timetable: weekly recurring schedule per section
    /leave/*       -> leave & OD requests (apply, approve, bulk OD for events)
    /skills/*      -> claim, verify/flag, view skills
    /projects/*    -> create, verify per member, view projects
    /mentor/*      -> AI career mentor chat
    /resume/*      -> AI resume builder + ATS scoring (student)
    /drives/*      -> placement drives, eligibility, applications & shortlisting
    /placement/analytics/* -> placement funnel, rate, per-drive & company stats
    /recruiters/*  -> recruiter portal: TPO onboards companies; recruiters self-onboard
    /people/*      -> staff roster: list students (optionally by section)
    /face/*        -> face attendance: enroll a student's reference face (staff)
    /announcements/* -> institute broadcasts (admin posts, everyone reads)
    /calendar/*    -> academic calendar (admin manages, everyone reads)
    /audit         -> append-only governance audit log (admin only)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from academics import router as academics_router
from admin import router as admin_router
from analytics import router as analytics_router
from announcements import router as announcements_router
from assignments import router as assignments_router
from attendance import router as attendance_router
from audit import router as audit_router
from auth import router as auth_router
from calendar_events import router as calendar_router
from config import settings
from db import engine
from doubts import router as doubts_router
from eca import router as eca_router
from face import router as face_router
from leads import router as leads_router
from leaveod import router as leaveod_router
from materials import router as materials_router
from mentor import router as mentor_router
from people import router as people_router
from placement import router as placement_router
from placement_analytics import router as placement_analytics_router
from projects import router as projects_router
from recruiters import router as recruiters_router
from resume import router as resume_router
from skills import router as skills_router
from timetable import router as timetable_router

app = FastAPI(title=settings.PROJECT_NAME, version="0.30.0")

# CORS: allow the local Next.js dev frontend to call the API from the browser.
# Add your deployed frontend origin(s) to this list when you go to production.
# Local dev origins are always allowed; production origins (e.g. the deployed
# Vercel URL) come from the CORS_ORIGINS env var (comma-separated).
_cors_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
_cors_origins += [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Feature routers. Add new modules here as they are built.
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(announcements_router)
app.include_router(calendar_router)
app.include_router(audit_router)
app.include_router(attendance_router)
app.include_router(academics_router)
app.include_router(analytics_router)
app.include_router(assignments_router)
app.include_router(materials_router)
app.include_router(doubts_router)
app.include_router(skills_router)
app.include_router(eca_router)
app.include_router(projects_router)
app.include_router(mentor_router)
app.include_router(resume_router)
app.include_router(placement_router)
app.include_router(placement_analytics_router)
app.include_router(recruiters_router)
app.include_router(leads_router)
app.include_router(people_router)
app.include_router(face_router)
app.include_router(timetable_router)
app.include_router(leaveod_router)


@app.get("/")
def root() -> dict:
    """Root endpoint - quick sanity check that the API process is alive."""
    return {"app": settings.PROJECT_NAME, "status": "ok"}


@app.get("/health")
def health() -> dict:
    """Liveness probe for deploys/monitoring. Dependency-free and fast."""
    return {"status": "healthy"}


@app.get("/db-check")
def db_check() -> dict:
    """Readiness probe: open a connection and run a trivial query."""
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"database": "connected"}
