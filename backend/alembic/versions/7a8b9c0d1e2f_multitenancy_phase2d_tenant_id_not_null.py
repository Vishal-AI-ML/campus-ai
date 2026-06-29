"""multitenancy phase2d: users.tenant_id NOT NULL

Revision ID: 7a8b9c0d1e2f
Revises: 522dfeadcde6
Create Date: 2026-06-29

Tightens users.tenant_id from nullable to NOT NULL. By this point every user
creation path sets a tenant (invite-accept, tenant-scoped /auth/register) and
Phase 1 backfilled existing rows. As a safety net we backfill any remaining
NULLs to the earliest tenant (the seeded default institute) BEFORE applying the
constraint, so the upgrade cannot fail on leftover orphan rows.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "7a8b9c0d1e2f"
down_revision = "522dfeadcde6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Safety backfill: assign any tenant-less users to the earliest tenant so
    # the NOT NULL constraint applies cleanly. No-op if there are none.
    op.execute(
        "UPDATE users SET tenant_id = (SELECT id FROM tenants ORDER BY id LIMIT 1) "
        "WHERE tenant_id IS NULL"
    )
    op.alter_column(
        "users",
        "tenant_id",
        existing_type=sa.Integer(),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "tenant_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
