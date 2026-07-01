"""Activate (or deactivate) a user account.

    uv run python activate_user.py <email>            # set is_active = true
    uv run python activate_user.py <email> off        # set is_active = false

Connects via DATABASE_URL (app_user). The users table has no RLS, and app_user
has UPDATE grant, so this works as the app role.
"""
import sys

from sqlalchemy import text

from db import engine

if len(sys.argv) < 2:
    print("usage: uv run python activate_user.py <email> [off]")
    raise SystemExit(1)

email = sys.argv[1]
active = not (len(sys.argv) > 2 and sys.argv[2].lower() in ("off", "false", "0"))

with engine.begin() as conn:
    result = conn.execute(
        text("UPDATE users SET is_active = :a WHERE email = :e"),
        {"a": active, "e": email},
    )
    print(f"is_active -> {active} for {email!r}: {result.rowcount} row(s) updated")

# Confirm
with engine.connect() as conn:
    row = conn.execute(
        text("SELECT email, role, is_active FROM users WHERE email = :e"),
        {"e": email},
    ).fetchone()
    print("now:", tuple(row) if row else "NOT FOUND")
