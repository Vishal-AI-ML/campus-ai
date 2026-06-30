"""phase4 rls batch 3d: FORCE RLS + tenant_isolation policy on remaining 23 tenant tables

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-30

Bulk roll-out of the same defense-in-depth pattern shipped for ``announcements``
(Batch 3b) and ``assignments`` (Batch 3c), now applied in ONE migration to every
remaining tenant-scoped table that carries a NOT NULL ``tenant_id``:

  * ENABLE + FORCE row level security on each table. FORCE is required so the
    policy also applies to the table *owner* role (used by migrations).
  * CREATE POLICY ``tenant_isolation`` FOR ALL using the per-connection GUC
    helper ``app.current_tenant_id()`` (created in b1c2d3e4f5a6). Both USING
    (read) and WITH CHECK (write) require ``tenant_id = app.current_tenant_id()``
    so a row can neither be read nor written across tenants. With the GUC unset
    ``app.current_tenant_id()`` is NULL -> default-deny (0 rows).

Whole migration runs in one transaction (Postgres transactional DDL): if any
statement fails, everything rolls back.

Intentionally EXCLUDED:
  * users / tenants / tenant_invites - read during auth / accept-invite BEFORE
    the request GUC is set; RLS here would break login / invite acceptance.
  * leads / feedback - nullable tenant_id with an admin "claim" flow; a strict
    ``tenant_id = app.current_tenant_id()`` policy would hide NULL (un-claimed)
    rows. Needs a bespoke ``tenant_id IS NULL OR ...`` policy later.
  * recruiters / recruiter_users / recruiter_invites / face_enrollments - no
    tenant_id by design (platform-global; isolation flows via drives).
  * announcements, assignments - already shipped in Batch 3b / 3c.

Postgres-only: guarded on the dialect so the SQLite test DB is skipped cleanly.
"""

from alembic import op

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None

# Every remaining tenant-scoped table with a NOT NULL tenant_id column.
TABLES = [
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


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
                FOR ALL
                USING (tenant_id = app.current_tenant_id())
                WITH CHECK (tenant_id = app.current_tenant_id())
            """
        )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
