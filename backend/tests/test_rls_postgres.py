"""Phase 5 - real-Postgres cross-tenant RLS isolation suite.

Why this is separate from the rest of the suite
-----------------------------------------------
The main test-suite runs against a throwaway SQLite DB (see ``conftest.py``),
where Postgres Row-Level Security is a no-op. The *real* security guarantee -
``FORCE ROW LEVEL SECURITY`` + a ``tenant_isolation`` policy on every
tenant-scoped table - can therefore only be proven against an actual Postgres
engine connected as the **NOBYPASSRLS** ``app_user`` role.

This module consolidates the manual ``rls_verify_all.py`` check into automated
pytest assertions so a regression (a forgotten policy, a missing FORCE, a role
with BYPASSRLS) fails CI instead of leaking across tenants silently.

How to run it
-------------
It is SKIPPED unless ``RLS_TEST_DATABASE_URL`` points at a Postgres database,
connected as the app role (NOT the owner / not a BYPASSRLS superuser):

    # PowerShell
    $env:RLS_TEST_DATABASE_URL = $env:DATABASE_URL   # the app_user URL
    uv run pytest tests/test_rls_postgres.py -v

Safety
------
Every write happens inside a single transaction that is ALWAYS rolled back, and
the tenant GUC is set transaction-locally (``is_local => true``). Nothing this
suite does is ever committed to the target database.
"""

import os
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.pool import NullPool

# --- Gate: only run against a real Postgres app-role connection --------------
_RLS_URL = os.environ.get("RLS_TEST_DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    "postgresql" not in _RLS_URL,
    reason=(
        "RLS_TEST_DATABASE_URL not set to a Postgres URL; real RLS can only be "
        "verified against Postgres connected as the NOBYPASSRLS app role."
    ),
)

# Every table that Phase 4 put under FORCE RLS + a tenant_isolation policy
# (Batch 3b announcements, 3c assignments, 3d the remaining 23). Keep this in
# lock-step with the migrations - if a new tenant-scoped table is added and
# protected, append it here so the default-deny check covers it too.
RLS_TABLES = [
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


@pytest.fixture(scope="module")
def engine():
    """A dedicated engine on the app role. NullPool => no GUC leaks between
    connections, pre_ping for the cloud pooler."""
    eng = create_engine(_RLS_URL, poolclass=NullPool, pool_pre_ping=True, future=True)
    try:
        yield eng
    finally:
        eng.dispose()


def _set_tenant(conn, tenant_id):
    """Set the RLS GUC transaction-locally (None => cleared / default-deny)."""
    conn.execute(
        text("SELECT set_config('app.current_tenant_id', :tid, true)"),
        {"tid": "" if tenant_id is None else str(tenant_id)},
    )


def _count(conn, table):
    return conn.execute(text(f'SELECT count(*) FROM "{table}"')).scalar()


def test_app_role_is_not_bypassing_rls(engine):
    """A role with BYPASSRLS would make every policy below meaningless, so we
    assert the connection's role is genuinely subject to RLS."""
    with engine.connect() as conn:
        bypasses = conn.execute(
            text(
                "SELECT rolbypassrls FROM pg_roles "
                "WHERE rolname = current_user"
            )
        ).scalar()
    assert bypasses is False, (
        "RLS_TEST_DATABASE_URL connects as a BYPASSRLS role - point it at the "
        "NOBYPASSRLS app_user, otherwise RLS isolation is not actually tested."
    )


def test_default_deny_with_no_tenant_set(engine):
    """With no tenant GUC, app.current_tenant_id() is NULL, so the
    `tenant_id = NULL` policy matches nothing: every protected table must
    return zero rows (default-deny). This is the `unset` column of
    rls_verify_all.py, asserted."""
    with engine.connect() as conn:
        _set_tenant(conn, None)  # explicit: no tenant in scope
        leaks = {t: _count(conn, t) for t in RLS_TABLES if _count(conn, t) != 0}
    assert leaks == {}, f"Tables visible with NO tenant set (RLS leak): {leaks}"


def test_cross_tenant_isolation_roundtrip(engine):
    """End-to-end proof on `departments`: a row created under tenant A is
    visible to A, invisible to tenant B, and invisible with no tenant set.
    Everything is rolled back, so nothing is committed to the database."""
    suffix = uuid.uuid4().hex[:8]
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            # `tenants` is intentionally NOT under RLS (read during auth before
            # the GUC exists), so we can seed two throwaway institutes.
            tenant_a = conn.execute(
                text(
                    "INSERT INTO tenants (name, slug, is_active) "
                    "VALUES (:n, :s, true) RETURNING id"
                ),
                {"n": f"RLS Test A {suffix}", "s": f"rls-test-a-{suffix}"},
            ).scalar()
            tenant_b = conn.execute(
                text(
                    "INSERT INTO tenants (name, slug, is_active) "
                    "VALUES (:n, :s, true) RETURNING id"
                ),
                {"n": f"RLS Test B {suffix}", "s": f"rls-test-b-{suffix}"},
            ).scalar()

            # Insert a department as tenant A (WITH CHECK must allow it).
            _set_tenant(conn, tenant_a)
            conn.execute(
                text(
                    "INSERT INTO departments (tenant_id, name, code) "
                    "VALUES (:t, :n, :c)"
                ),
                {"t": tenant_a, "n": f"CSE {suffix}", "c": f"C{suffix[:6]}"},
            )

            # Tenant A sees exactly its own row...
            assert _count(conn, "departments") == 1

            # ...tenant B sees nothing of A's...
            _set_tenant(conn, tenant_b)
            assert _count(conn, "departments") == 0

            # ...and with no tenant set, default-deny hides it too.
            _set_tenant(conn, None)
            assert _count(conn, "departments") == 0
        finally:
            trans.rollback()


def test_with_check_blocks_cross_tenant_insert(engine):
    """WITH CHECK must forbid writing a row stamped for a different tenant than
    the one in scope - i.e. tenant A cannot forge a row for tenant B."""
    suffix = uuid.uuid4().hex[:8]
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            tenant_a = conn.execute(
                text(
                    "INSERT INTO tenants (name, slug, is_active) "
                    "VALUES (:n, :s, true) RETURNING id"
                ),
                {"n": f"RLS Chk A {suffix}", "s": f"rls-chk-a-{suffix}"},
            ).scalar()
            tenant_b = conn.execute(
                text(
                    "INSERT INTO tenants (name, slug, is_active) "
                    "VALUES (:n, :s, true) RETURNING id"
                ),
                {"n": f"RLS Chk B {suffix}", "s": f"rls-chk-b-{suffix}"},
            ).scalar()

            _set_tenant(conn, tenant_a)
            with pytest.raises(DBAPIError):
                conn.execute(
                    text(
                        "INSERT INTO departments (tenant_id, name, code) "
                        "VALUES (:t, :n, :c)"
                    ),
                    {"t": tenant_b, "n": f"Forge {suffix}", "c": f"F{suffix[:6]}"},
                )
        finally:
            trans.rollback()
