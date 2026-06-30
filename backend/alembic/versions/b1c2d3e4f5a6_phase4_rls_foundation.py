"""phase4 rls foundation: app.current_tenant_id() helper (NO policies yet)

Revision ID: b1c2d3e4f5a6
Revises: a9b0c1d2e3f4
Create Date: 2026-06-30

Phase 4 adds Postgres Row-Level Security (RLS) as *defense-in-depth* on top of
the app-layer ``WHERE tenant_id == ...`` filtering we already do everywhere.

This FIRST batch is intentionally a no-op for query *results*: it enables ZERO
policies, so it cannot hide rows or cause an outage. It only lays the
foundation:

  * schema ``app`` - a namespace for our RLS helpers.
  * function ``app.current_tenant_id()`` - reads the per-connection GUC
    ``app.current_tenant_id`` (set by the backend on each authenticated
    request, see db.set_current_tenant) and returns it as an int, or NULL when
    unset. Uses the two-arg ``current_setting(name, missing_ok => true)`` form
    so it never errors when the GUC is absent (migrations, psql, etc.). Future
    per-table policies will read ``tenant_id = app.current_tenant_id()``.

Postgres-only: guarded on the dialect so a non-Postgres bind (the SQLite test
DB) is skipped cleanly.
"""

from alembic import op

revision = "b1c2d3e4f5a6"
down_revision = "a9b0c1d2e3f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("CREATE SCHEMA IF NOT EXISTS app")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app.current_tenant_id()
        RETURNS integer
        LANGUAGE sql
        STABLE
        AS $func$
            SELECT NULLIF(current_setting('app.current_tenant_id', true), '')::integer
        $func$
        """
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("DROP FUNCTION IF EXISTS app.current_tenant_id()")
    op.execute("DROP SCHEMA IF EXISTS app")
