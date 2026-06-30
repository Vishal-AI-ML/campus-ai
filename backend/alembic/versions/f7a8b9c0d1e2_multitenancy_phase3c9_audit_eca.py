"""multitenancy phase3c batch9: tenant_id on audit_logs + extracurriculars

Gives `audit_logs` and `extracurriculars` a tenant_id so every query can be
tenant-filtered (and a future Postgres RLS policy can enforce it).

Inheritance of the tenant on backfill:
  * audit_logs       -> from the actor (audit_logs.actor_id -> users); actor_id
                        is SET NULL-able, so orphan rows fall back to the
                        earliest tenant via the safety net.
  * extracurriculars -> from the student (extracurriculars.student_id -> users);
                        student_id is NOT NULL, so the safety net is just
                        defence-in-depth.

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-06-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f7a8b9c0d1e2"
down_revision: str | None = "e6f7a8b9c0d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Safety net: rows whose inheritance source is NULL get the earliest tenant
# (single-tenant production today, so this is always the right institute).
_EARLIEST_TENANT = "(SELECT id FROM tenants ORDER BY id LIMIT 1)"

_TABLES = ("audit_logs", "extracurriculars")


def _add_tenant_column(table: str) -> None:
    """Add a nullable tenant_id + its index + FK (NOT NULL set later)."""
    op.add_column(table, sa.Column("tenant_id", sa.Integer(), nullable=True))
    op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])
    op.create_foreign_key(
        f"fk_{table}_tenant_id_tenants",
        table,
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )


def _backfill_from(table: str, fk_column: str, parent_table: str) -> None:
    """Copy tenant_id from the parent row referenced by `fk_column`."""
    op.execute(
        f"UPDATE {table} SET tenant_id = "
        f"(SELECT tenant_id FROM {parent_table} "
        f"WHERE {parent_table}.id = {table}.{fk_column}) "
        f"WHERE tenant_id IS NULL"
    )
    # Orphan rows (NULL fk, or a parent without a tenant) -> earliest tenant.
    op.execute(
        f"UPDATE {table} SET tenant_id = {_EARLIEST_TENANT} "
        f"WHERE tenant_id IS NULL"
    )


def upgrade() -> None:
    for table in _TABLES:
        _add_tenant_column(table)

    _backfill_from("audit_logs", "actor_id", "users")
    _backfill_from("extracurriculars", "student_id", "users")

    for table in _TABLES:
        op.alter_column(
            table, "tenant_id", existing_type=sa.Integer(), nullable=False
        )


def downgrade() -> None:
    for table in reversed(_TABLES):
        op.drop_constraint(
            f"fk_{table}_tenant_id_tenants", table, type_="foreignkey"
        )
        op.drop_index(f"ix_{table}_tenant_id", table_name=table)
        op.drop_column(table, "tenant_id")
