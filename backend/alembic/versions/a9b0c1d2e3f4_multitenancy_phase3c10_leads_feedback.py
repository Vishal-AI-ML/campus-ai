"""multitenancy phase3c batch10: nullable tenant_id on leads + feedback

Revision ID: a9b0c1d2e3f4
Revises: f7a8b9c0d1e2
Create Date: 2026-06-30

Unlike every other Phase 3c table, ``leads`` and ``feedback`` are PUBLIC,
pre-signup submissions (prospects are not users yet, feedback can be
logged-out). So their ``tenant_id`` is **NULLABLE** and is intentionally NOT
backfilled: existing and incoming rows stay NULL until an admin explicitly
claims a lead into their institute (see ``leads.claim_lead``). There is no
NOT NULL step. FK is SET NULL so deleting an institute keeps the marketing
data, just unlinked.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "a9b0c1d2e3f4"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None

_TABLES = ("leads", "feedback")


def upgrade() -> None:
    for table in _TABLES:
        op.add_column(
            table,
            sa.Column("tenant_id", sa.Integer(), nullable=True),
        )
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])
        op.create_foreign_key(
            f"fk_{table}_tenant_id_tenants",
            table,
            "tenants",
            ["tenant_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    for table in _TABLES:
        op.drop_constraint(
            f"fk_{table}_tenant_id_tenants", table, type_="foreignkey"
        )
        op.drop_index(f"ix_{table}_tenant_id", table_name=table)
        op.drop_column(table, "tenant_id")
