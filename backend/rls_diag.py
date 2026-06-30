"""
Diagnose why announcements RLS is not filtering (Phase 4 Batch 3b).

Prints, using the SAME engine/role the app uses:
  - which DB role we connect as, and whether it is superuser / BYPASSRLS
  - whether RLS is ENABLED and FORCED on announcements
  - which policies exist on announcements
  - current alembic head in the DB
  - the table owner

Usage:
    uv run python rls_diag.py
"""
from sqlalchemy import text

from db import engine


def main():
    with engine.connect() as conn:
        def q(sql):
            return conn.execute(text(sql)).fetchall()

        print("connect role (current/session):",
              q("SELECT current_user, session_user"))
        print("role flags [rolname, superuser, bypassrls]:",
              q("SELECT rolname, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"))
        print("announcements [rls_enabled, rls_forced]:",
              q("SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname = 'announcements'"))
        print("policies on announcements:",
              q("SELECT polname FROM pg_policy WHERE polrelid = 'announcements'::regclass"))
        print("alembic version in DB:",
              q("SELECT version_num FROM alembic_version"))
        print("announcements owner:",
              q("SELECT tableowner FROM pg_tables WHERE tablename = 'announcements'"))


if __name__ == "__main__":
    main()
