"""
One-off prod RLS verifier for ALL tenant-isolated tables (Phase 4).

Runs three counts per table on a SINGLE DB connection using the SAME engine/role
the app uses (imported from db.py), toggling the session GUC
app.current_tenant_id:

  tenant_id='1' -> only tenant 1 rows
  tenant_id='2' -> only tenant 2 rows
  tenant_id=''  -> MUST be 0 (default-deny). If > 0 the DB role is bypassing
                  RLS (superuser/BYPASSRLS) and FORCE is not enough.

Usage (after `uv run alembic upgrade head`):
    uv run python rls_verify_all.py

PASS = every table shows 0 in the 'unset' column (no cross-tenant leak).
"""
from sqlalchemy import text

from db import engine

# Tables protected by a tenant_isolation RLS policy (3b + 3c + 3d).
TABLES = [
    "announcements",
    "assignments",
    "departments",
    "sections",
    "subjects",
    "attendance_records",
    "results",
    "skills",
    "projects",
    "project_members",
    "extracurriculars",
    "internships",
    "resumes",
    "drives",
    "applications",
    "offers",
    "calendar_events",
    "audit_logs",
    "submissions",
    "materials",
    "doubts",
    "doubt_answers",
    "answer_votes",
    "timetable_entries",
    "leave_requests",
]


def _count(conn, table):
    return conn.execute(text(f"SELECT count(*) FROM {table}")).scalar()


def main():
    print("DB dialect:", engine.dialect.name)
    header = f"{'table':<22}{'t1':<7}{'t2':<7}{'unset':<7}"
    print(header)
    print("-" * len(header))
    any_leak = False
    with engine.connect() as conn:
        for table in TABLES:
            counts = {}
            for tid in ("1", "2", ""):
                conn.execute(
                    text("SELECT set_config('app.current_tenant_id', :v, false)"),
                    {"v": tid},
                )
                counts[tid] = _count(conn, table)
            leak = counts[""] != 0
            any_leak = any_leak or leak
            flag = "  <-- LEAK!" if leak else ""
            print(
                f"{table:<22}{counts['1']:<7}{counts['2']:<7}{counts['']:<7}{flag}"
            )
    print()
    if any_leak:
        print("FAIL: a table returned rows with unset tenant -> RLS NOT enforced.")
    else:
        print("PASS: every table is 0 rows on unset tenant (default-deny enforced).")


if __name__ == "__main__":
    main()
