"""multitenancy phase3c batch3: tenant_id on staff-created tables

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-06-29

Batch 3 of Phase 3c. These four tables are *staff-created broadcasts* rather
than student-owned rows, so each one derives its tenant from the staff member
who created it (a different FK column per table):

  * drives          -> created_by_id   (the TPO who posted the drive)
  * announcements   -> author_id        (the admin who posted it)
  * assignments     -> created_by_id    (the teacher who posted it)
  * materials       -> uploaded_by_id   (the teacher/admin who uploaded it)

Same proven 4-step pattern as the earlier batches:
  1) add tenant_id NULLABLE so existing rows survive,
  2) backfill from the creator's tenant,
  3) safety-net leftover NULLs (creator FK is SET NULL, so some may be orphan)
     to the earliest (seeded) tenant,
  4) add FK + index, then tighten to NOT NULL.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "a7b8c9d0e1f2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None

# (table, creator FK column) - each creator column points at users.id.
_TABLES = (
    ("drives", "created_by_id"),
    ("announcements", "author_id"),
    ("assignments", "created_by_id"),
    ("materials", "uploaded_by_id"),
)


def upgrade() -> None:
    for table, creator_col in _TABLES:
        # 1) Nullable first so existing rows don't violate NOT NULL mid-migration.
        op.add_column(
            table, sa.Column("tenant_id", sa.Integer(), nullable=True)
        )
        # 2) Backfill: each row inherits the creating staff member's tenant.
        op.execute(
            f"UPDATE {table} SET tenant_id = "
            f"(SELECT tenant_id FROM users WHERE users.id = {table}.{creator_col}) "
            f"WHERE tenant_id IS NULL"
        )
        # 3) Safety net: the creator FK is SET NULL, so a deleted creator can
        #    leave an orphan row -> fall back to the earliest (seeded) tenant.
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
    for table, _creator_col in reversed(_TABLES):
        op.drop_index(f"ix_{table}_tenant_id", table_name=table)
        op.drop_constraint(f"fk_{table}_tenant_id", table, type_="foreignkey")
        op.drop_column(table, "tenant_id")
