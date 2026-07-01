"""app_user-only RLS picture (no postgres password needed).
For each table: is RLS enabled/forced, does app_user have SELECT, how many
policies exist, and the visible row count. Reveals RLS-enabled-but-no-policy
(which denies all rows to a non-bypass role like app_user).

    uv run python diag_rls.py
"""
from sqlalchemy import text
from db import engine

TABLES = ("tenants", "users", "announcements")

with engine.connect() as c:
    who = c.execute(text("SELECT current_user, current_database()")).fetchone()
    print(f"connected as {who[0]} on db {who[1]}\n")
    print(f"{'table':14} {'rls_on':7} {'forced':7} {'select?':8} {'policies':9} {'count'}")
    for t in TABLES:
        rls = c.execute(text(
            "SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname = :t"
        ), {"t": t}).fetchone()
        cansel = c.execute(text(
            "SELECT has_table_privilege(current_user, :t, 'SELECT')"
        ), {"t": t}).scalar()
        npol = c.execute(text(
            "SELECT count(*) FROM pg_policies WHERE tablename = :t"
        ), {"t": t}).scalar()
        try:
            n = c.execute(text(f'SELECT count(*) FROM "{t}"')).scalar()
        except Exception as e:
            n = f"ERR {type(e).__name__}"
        en = rls[0] if rls else "?"
        fo = rls[1] if rls else "?"
        print(f"{t:14} {str(en):7} {str(fo):7} {str(cansel):8} {str(npol):9} {n}")
