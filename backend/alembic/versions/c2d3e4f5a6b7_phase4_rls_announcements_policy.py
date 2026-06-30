"""phase4 rls batch 3b: FIRST real RLS policy + FORCE on announcements

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-06-30

This is the FIRST batch where Postgres Row-Level Security actually *filters
rows* (Batch 1 only added the `app.current_tenant_id()` helper; Batch 2/3 only
set the per-request GUC in code, no policies). We turn it on for a single,
low-risk pilot table -- ``announcements`` -- before rolling out table by table.

What this does (Postgres only):
  * ENABLE ROW LEVEL SECURITY on ``announcements``.
  * FORCE ROW LEVEL SECURITY -- our app connects as the table OWNER
    (``postgres``), and the owner BYPASSES RLS unless FORCE is set, so FORCE is
    mandatory for the policy to actually apply to our queries.
  * CREATE POLICY ``tenant_isolation`` FOR ALL
      USING       (tenant_id = app.current_tenant_id())   -- which rows are visible
      WITH CHECK  (tenant_id = app.current_tenant_id())   -- which rows may be written

Behaviour:
  * Each authenticated request sets the GUC ``app.current_tenant_id`` to the
    caller's institute (db.set_current_tenant, called from get_current_user),
    so a request only ever sees / writes its own institute's announcements.
  * If the GUC is unset, ``app.current_tenant_id()`` returns NULL and
    ``tenant_id = NULL`` is never true => DEFAULT-DENY (zero rows). This is why
    the GUC-setting code (Batch 2/3) MUST be deployed before this migration is
    applied to prod -- otherwise legitimate requests would see no rows.
  * App-layer ``WHERE tenant_id == ...`` filtering stays in place; RLS is
    defense-in-depth underneath it.

Postgres-only: guarded on the dialect, so the SQLite test DB skips this cleanly
and the existing app-layer announcements isolation test keeps proving behaviour
there.
"""

from alembic import op

revision = "c2d3e4f5a6b7"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("ALTER TABLE announcements ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE announcements FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON announcements
            FOR ALL
            USING (tenant_id = app.current_tenant_id())
            WITH CHECK (tenant_id = app.current_tenant_id())
        """
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON announcements")
    op.execute("ALTER TABLE announcements NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE announcements DISABLE ROW LEVEL SECURITY")
