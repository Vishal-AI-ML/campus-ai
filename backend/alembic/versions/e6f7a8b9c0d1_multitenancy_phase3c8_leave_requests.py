"""multitenancy phase3c batch8: tenant_id on leave_requests

Gives `leave_requests` a tenant_id so every leave/OD query can be tenant-
filtered (and a future Postgres RLS policy can enforce it).

Inheritance on backfill:
  * leave_requests -> from the student the request is FOR
                      (leave_requests.student_id -> users)

student_id is NOT NULL, so the only orphan case is a student row that somehow
lacks a tenant; the earliest-tenant safety net covers it (single-tenant prod
today, so it is always the right institute).

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-06-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e6f7a8b9c0d1"
down_revision: str | None = "d5e6f7a8b9c0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Safety net: rows whose inheritance source is NULL get the earliest tenant.
_EARLIEST_TENANT = "(SELECT id FROM tenants ORDER BY id LIMIT 1)"

_TABLE = "leave_requests"


def upgrade() -> None:
    op.add_column(_TABLE, sa.Column("tenant_id", sa.Integer(), nullable=True))
    op.create_index(f"ix_{_TABLE}_tenant_id", _TABLE, ["tenant_id"])
    op.create_foreign_key(
        f"fk_{_TABLE}_tenant_id_tenants",
        _TABLE,
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # Backfill the tenant from the student the request is for.
    op.execute(
        f"UPDATE {_TABLE} SET tenant_id = "
        f"(SELECT tenant_id FROM users WHERE users.id = {_TABLE}.student_id) "
        f"WHERE tenant_id IS NULL"
    )
    # Orphans (missing student / tenant) -> earliest tenant.
    op.execute(
        f"UPDATE {_TABLE} SET tenant_id = {_EARLIEST_TENANT} "
        f"WHERE tenant_id IS NULL"
    )
    op.alter_column(
        _TABLE, "tenant_id", existing_type=sa.Integer(), nullable=False
    )


def downgrade() -> None:
    op.drop_constraint(
        f"fk_{_TABLE}_tenant_id_tenants", _TABLE, type_="foreignkey"
    )
    op.drop_index(f"ix_{_TABLE}_tenant_id", table_name=_TABLE)
    op.drop_column(_TABLE, "tenant_id")
