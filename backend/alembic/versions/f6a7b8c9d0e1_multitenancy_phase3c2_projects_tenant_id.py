"""multitenancy phase3c batch2: projects.tenant_id + project_members.tenant_id

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-06-29

Projects are owner-owned (like skills); project_members are child rows that
inherit the parent project's tenant. ORDER MATTERS: we backfill `projects`
FIRST, then `project_members` can read the now-populated project tenant.

Pattern per table: add nullable -> backfill -> safety-net -> FK + index ->
NOT NULL.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- projects first (members derive their tenant from the project) ------
    op.add_column(
        "projects", sa.Column("tenant_id", sa.Integer(), nullable=True)
    )
    op.execute(
        "UPDATE projects SET tenant_id = "
        "(SELECT tenant_id FROM users WHERE users.id = projects.owner_id) "
        "WHERE tenant_id IS NULL"
    )
    op.execute(
        "UPDATE projects SET tenant_id = "
        "(SELECT id FROM tenants ORDER BY id LIMIT 1) WHERE tenant_id IS NULL"
    )
    op.create_foreign_key(
        "fk_projects_tenant_id",
        "projects",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_projects_tenant_id", "projects", ["tenant_id"])
    op.alter_column(
        "projects", "tenant_id", existing_type=sa.Integer(), nullable=False
    )

    # --- project_members inherit tenant from their (populated) project ------
    op.add_column(
        "project_members", sa.Column("tenant_id", sa.Integer(), nullable=True)
    )
    op.execute(
        "UPDATE project_members SET tenant_id = "
        "(SELECT tenant_id FROM projects "
        "WHERE projects.id = project_members.project_id) "
        "WHERE tenant_id IS NULL"
    )
    op.execute(
        "UPDATE project_members SET tenant_id = "
        "(SELECT id FROM tenants ORDER BY id LIMIT 1) WHERE tenant_id IS NULL"
    )
    op.create_foreign_key(
        "fk_project_members_tenant_id",
        "project_members",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_project_members_tenant_id", "project_members", ["tenant_id"]
    )
    op.alter_column(
        "project_members",
        "tenant_id",
        existing_type=sa.Integer(),
        nullable=False,
    )


def downgrade() -> None:
    for table in ("project_members", "projects"):
        op.drop_index(f"ix_{table}_tenant_id", table_name=table)
        op.drop_constraint(f"fk_{table}_tenant_id", table, type_="foreignkey")
        op.drop_column(table, "tenant_id")
