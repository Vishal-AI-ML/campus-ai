"""
One-off prod RLS verifier for announcements (Phase 4 Batch 3b).

Runs three counts on a SINGLE DB connection using the SAME engine/role the app
uses (imported from db.py), toggling the session GUC app.current_tenant_id:

  tenant_id='1' -> only tenant 1 rows
  tenant_id='2' -> only tenant 2 rows
  tenant_id=''  -> MUST be 0 (default-deny). If > 0, the DB role is bypassing
                  RLS (superuser/BYPASSRLS) and FORCE is not enough.

Usage (after `uv run alembic upgrade head`):
    uv run python rls_verify.py
"""
from sqlalchemy import text

from db import engine


def _count(conn):
    return conn.execute(text("SELECT count(*) FROM announcements")).scalar()


def main():
    print("DB dialect:", engine.dialect.name)
    with engine.connect() as conn:
        for tid in ("1", "2", ""):
            conn.execute(
                text("SELECT set_config('app.current_tenant_id', :v, false)"),
                {"v": tid},
            )
            shown = repr(tid) if tid else "'' (unset)"
            print(f"  app.current_tenant_id = {shown:<12} -> announcements count = {_count(conn)}")
    print("\nPASS if: tenant 1 count > 0  AND  unset count == 0")


if __name__ == "__main__":
    main()
