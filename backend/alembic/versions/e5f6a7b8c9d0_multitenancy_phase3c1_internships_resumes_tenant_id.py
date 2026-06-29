"""multitenancy phase3c batch1: internships.tenant_id + resumes.tenant_id

Revision ID: e5f6a7b8c9d0
Revises: d3e4f5a6b7c8
Create Date: 2026-06-29

Applies the Phase 3 pilot pattern (proven on `skills`) to the next two
student-owned tables. Both rows derive their tenant from the owning student:

  1) add tenant_id NULLABLE so existing rows survive,
  2) backfill from the student's tenant,
  3) safety-net leftover NULLs to the earliest tenant,
  4) add FK + index, then tighten to NOT NULL.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "e5f6a7b8c9d0"
down_revision = "d3e4f5a6b7c8"
branch_labels = None
depends_on = None

# Both tables hang off the student (users.id), so the backfill is identical.
_TABLES = ("internships", "resumes")


def upgrade() -> None:
    for table in _TABLES:
        # 1) Nullable first so existing rows don't violate NOT NULL mid-migration.
        op.add_column(
            table, sa.Column("tenant_id", sa.Integer(), nullable=True)
        )
        # 2) Backfill: each row inherits its student's tenant.
        op.execute(
            f"UPDATE {table} SET tenant_id = "
            f"(SELECT tenant_id FROM users WHERE users.id = {table}.student_id) "
            f"WHERE tenant_id IS NULL"
        )
        # 3) Safety net for any orphan rows -> earliest (seeded) tenant.
        op.execute(
            f"UPDATE {table} SET tenant_id = "
            f"(SELECT id FROM tenants ORDER BY id LIMIT 1) "
            f"WHERE tenant_id IS NULL"
        )
        # 4) FK + index, then enforce NOT NULL.
        op.create_foreign_key(
            f"fk_{table}_tenant_id",
            table,
            "tenants",
            ["tenant_id"],
            ["id"],
            ondelete="CASCADE",
        )
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])
        op.alter_column(
            table,
            "tenant_id",
            existing_type=sa.Integer(),
            nullable=False,
        )


def downgrade() -> None:
    for table in _TABLES:
        op.drop_index(f"ix_{table}_tenant_id", table_name=table)
        op.drop_constraint(f"fk_{table}_tenant_id", table, type_="foreignkey")
        op.drop_column(table, "tenant_id")
