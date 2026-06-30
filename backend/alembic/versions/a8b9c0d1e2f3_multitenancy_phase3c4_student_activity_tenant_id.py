"""multitenancy phase3c batch4: tenant_id on student-activity tables

Revision ID: a8b9c0d1e2f3
Revises: a7b8c9d0e1f2
Create Date: 2026-06-29

Batch 4 of Phase 3c. These five tables are *student-activity* rows (attendance,
assignment submissions, and the doubt forum), so each one derives its tenant
from the user who created the row (a different FK column per table):

  * attendance_records -> student_id      (the student the record is about)
  * submissions        -> student_id      (the student who submitted)
  * doubts             -> asked_by_id      (the user who asked)
  * doubt_answers      -> answered_by_id   (the user who answered)
  * answer_votes       -> user_id          (the user who voted)

Same proven 4-step pattern as the earlier batches:
  1) add tenant_id NULLABLE so existing rows survive,
  2) backfill from the creator's tenant,
  3) safety-net leftover NULLs (some creator FKs are SET NULL, so a deleted
     user can leave an orphan row) to the earliest (seeded) tenant,
  4) add FK + index, then tighten to NOT NULL.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "a8b9c0d1e2f3"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None

# (table, creator FK column) - each creator column points at users.id.
_TABLES = (
    ("attendance_records", "student_id"),
    ("submissions", "student_id"),
    ("doubts", "asked_by_id"),
    ("doubt_answers", "answered_by_id"),
    ("answer_votes", "user_id"),
)


def upgrade() -> None:
    for table, creator_col in _TABLES:
        # 1) Nullable first so existing rows don't violate NOT NULL mid-migration.
        op.add_column(
            table, sa.Column("tenant_id", sa.Integer(), nullable=True)
        )
        # 2) Backfill: each row inherits the creating user's tenant.
        op.execute(
            f"UPDATE {table} SET tenant_id = "
            f"(SELECT tenant_id FROM users WHERE users.id = {table}.{creator_col}) "
            f"WHERE tenant_id IS NULL"
        )
        # 3) Safety net: some creator FKs are SET NULL, so a deleted creator can
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
