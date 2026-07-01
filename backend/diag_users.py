"""Compare row visibility between the app role (app_user, via DATABASE_URL) and
the owner role (postgres, via MIGRATION_DATABASE_URL). Reveals whether tables
are empty vs hidden by RLS/permissions.

    uv run python diag_users.py
"""
from sqlalchemy import create_engine, text
from config import settings
from db import engine as app_engine

mig_url = settings.MIGRATION_DATABASE_URL or settings.DATABASE_URL
mig_engine = create_engine(mig_url, future=True)

TABLES = ("tenants", "users", "announcements")


def report(eng, label):
    with eng.connect() as c:
        who = c.execute(text("SELECT current_user, current_database()")).fetchone()
        sp = c.execute(text("SHOW search_path")).scalar()
        print(f"[{label}] role={who[0]} db={who[1]} search_path={sp}")
        for t in TABLES:
            try:
                n = c.execute(text(f'SELECT count(*) FROM {t}')).scalar()
                print(f"    {t:14} -> {n}")
            except Exception as e:
                print(f"    {t:14} -> ERR {type(e).__name__}: {str(e)[:90]}")


report(app_engine, "app_user (DATABASE_URL)")
print()
report(mig_engine, "postgres (MIGRATION_DATABASE_URL)")
print()
with mig_engine.connect() as c:
    rows = c.execute(text(
        "SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class "
        "WHERE relname IN ('tenants','users','announcements') ORDER BY relname"
    )).fetchall()
    print("RLS flags [table, enabled, forced]:")
    for r in rows:
        print("   ", tuple(r))
