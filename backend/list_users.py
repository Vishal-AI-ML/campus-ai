"""List tenants + users in whatever DB DATABASE_URL points at (prod = app_user).
Users table has no RLS, so app_user can read all rows.

    uv run python list_users.py
"""
from sqlalchemy import text
from db import engine

with engine.connect() as conn:
    print("=== Tenants ===")
    for r in conn.execute(text("SELECT id, slug, name FROM tenants ORDER BY id")):
        print(f"  id={r[0]}  slug={r[1]!r}  name={r[2]!r}")
    print("\n=== Users (email | role | tenant_id | name) ===")
    rows = conn.execute(text(
        "SELECT email, role, tenant_id, full_name FROM users ORDER BY tenant_id, role"
    )).fetchall()
    for r in rows:
        print(f"  {r[0]!r:40} | {str(r[1]):10} | tenant {r[2]} | {r[3]!r}")
    print(f"\n  total users: {len(rows)}")
