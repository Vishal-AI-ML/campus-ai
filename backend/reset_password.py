"""Reset one user's password in the DB DATABASE_URL points at.
Users table has no RLS so app_user (UPDATE granted) can do this.

    uv run python reset_password.py <email> <new_password>

Example:
    uv run python reset_password.py boss@campus.ai Admin@12345
"""
import sys
from sqlalchemy import text
from db import engine
from security import hash_password

if len(sys.argv) != 3:
    print("usage: uv run python reset_password.py <email> <new_password>")
    raise SystemExit(1)

email, new_pw = sys.argv[1], sys.argv[2]
hashed = hash_password(new_pw)
with engine.begin() as conn:
    res = conn.execute(
        text("UPDATE users SET hashed_password = :h WHERE email = :e"),
        {"h": hashed, "e": email},
    )
    print(f"rows updated for {email!r}: {res.rowcount}")
    if res.rowcount == 0:
        print("  (no user with that exact email - check list_users.py output)")
