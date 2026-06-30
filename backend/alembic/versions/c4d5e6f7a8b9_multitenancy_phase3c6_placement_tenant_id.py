"""multitenancy phase3c batch6: tenant_id on placement pipeline tables

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-06-30

Batch 6 of Phase 3c. The placement pipeline: applications and offers.

Tenant inheritance:
  * applications -> from their parent drive (drives.tenant_id)
  * offers       -> from their parent drive (drives.tenant_id)

Note on offers + recruiters: a recruiter (company) can span many institutes,
so `recruiters` is intentionally NOT tenant-scoped. An offer therefore inherits
its tenant from the DRIVE it was made on (an institute-owned object), never
from the recruiter. The existing unique constraints
(uq_application_drive_student, uq_offer_application) are already drive/
application-scoped, so once the rows are tenant-bound they stay safe as-is.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "c4d5e6f7a8b9"
down_revision = "b3c4d5e6f7a8"
branch_labels = None
depends_on = None

_EARLIEST_TENANT = "(SELECT id FROM tenants ORDER BY id LIMIT 1)"


def _add_tenant_column(table: str) -> None:
    """Add tenant_id nullable, FK + index (NOT NULL is set later per table)."""
    op.add_column(table, sa.Column("tenant_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        f"fk_{table}_tenant_id",
        table,
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])


def _backfill_from_drive(table: str) -> None:
    """Inherit tenant_id from the parent drive, then a safety net."""
    op.execute(
        f"UPDATE {table} SET tenant_id = "
        f"(SELECT tenant_id FROM drives WHERE drives.id = {table}.drive_id) "
        f"WHERE tenant_id IS NULL"
    )
    op.execute(
        f"UPDATE {table} SET tenant_id = {_EARLIEST_TENANT} "
        f"WHERE tenant_id IS NULL"
    )


def upgrade() -> None:
    # --- applications: inherit tenant from their drive ---
    _add_tenant_column("applications")
    _backfill_from_drive("applications")
    op.alter_column(
        "applications", "tenant_id", existing_type=sa.Integer(), nullable=False
    )

    # --- offers: inherit tenant from their drive (NOT the recruiter) ---
    _add_tenant_column("offers")
    _backfill_from_drive("offers")
    op.alter_column(
        "offers", "tenant_id", existing_type=sa.Integer(), nullable=False
    )


def downgrade() -> None:
    # offers
    op.drop_index("ix_offers_tenant_id", table_name="offers")
    op.drop_constraint("fk_offers_tenant_id", "offers", type_="foreignkey")
    op.drop_column("offers", "tenant_id")

    # applications
    op.drop_index("ix_applications_tenant_id", table_name="applications")
    op.drop_constraint(
        "fk_applications_tenant_id", "applications", type_="foreignkey"
    )
    op.drop_column("applications", "tenant_id")
