"""phase4 rls batch 3c: FORCE RLS + tenant_isolation policy on assignments

Revision ID: c3d4e5f6a7b8
Revises: c2d3e4f5a6b7
Create Date: 2026-06-30

Same defense-in-depth pattern we shipped for ``announcements`` (Batch 3b), now
applied to ``assignments``:

  * ENABLE + FORCE row level security on the table. FORCE is required so the
    policy also applies to the *table owner* role; without it the owner (used
    by migrations) silently bypasses RLS.
  * CREATE POLICY ``tenant_isolation`` FOR ALL using the per-connection GUC
    helper ``app.current_tenant_id()`` (created in b1c2d3e4f5a6). Both USING
    (read path) and WITH CHECK (write path) require
    ``tenant_id = app.current_tenant_id()`` so a row can neither be read nor
    written across tenants.

With the GUC unset (e.g. an unauthenticated/background connection),
``app.current_tenant_id()`` returns NULL and ``tenant_id = NULL`` is never true
-> default-deny (0 rows). The app sets the GUC per authenticated request via
db.set_current_tenant.

Postgres-only: guarded on the dialect so the SQLite test DB is skipped cleanly.
"""

from alembic import op

revision = "c3d4e5f6a7b8"
down_revision = "c2d3e4f5a6b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("ALTER TABLE assignments ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE assignments FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON assignments
            FOR ALL
            USING (tenant_id = app.current_tenant_id())
            WITH CHECK (tenant_id = app.current_tenant_id())
        """
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON assignments")
    op.execute("ALTER TABLE assignments NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE assignments DISABLE ROW LEVEL SECURITY")
