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
  * Placement: drives + verified-data eligibility engine.
  * Placement applications: students apply to eligible drives; TPO shortlists.

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
    /attendance/*  -> mark & view attendance
    /academics/*   -> subjects, results & SGPA/CGPA
    /skills/*      -> claim, verify/flag, view skills
    /projects/*    -> create, verify per member, view projects
    /mentor/*      -> AI career mentor chat
    /drives/*      -> placement drives, eligibility, applications & shortlisting
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from academics import router as academics_router
from admin import router as admin_router
from attendance import router as attendance_router
from auth import router as auth_router
from config import settings
from db import engine
from mentor import router as mentor_router
from placement import router as placement_router
from projects import router as projects_router
from skills import router as skills_router

app = FastAPI(title=settings.PROJECT_NAME, version="0.11.1")

# CORS: allow the local Next.js dev frontend to call the API from the browser.
# Add your deployed frontend origin(s) to this list when you go to production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Feature routers. Add new modules here as they are built.
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(attendance_router)
app.include_router(academics_router)
app.include_router(skills_router)
app.include_router(projects_router)
app.include_router(mentor_router)
app.include_router(placement_router)


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
