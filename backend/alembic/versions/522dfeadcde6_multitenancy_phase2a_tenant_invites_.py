"""multitenancy phase2a: tenant_invites table

Revision ID: 522dfeadcde6
Revises: 6357ee539628
Create Date: 2026-06-29

Note: `user_role` and `invite_status` Postgres ENUM types already exist (they
were created by earlier migrations for the `users` and `recruiter_invites`
tables). We therefore reference them with `create_type=False` so this
migration does NOT try to `CREATE TYPE` them again.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "522dfeadcde6"
down_revision = "6357ee539628"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant_invites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM(
                "student",
                "teacher",
                "tpo",
                "admin",
                "recruiter",
                name="user_role",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending",
                "accepted",
                "revoked",
                "expired",
                name="invite_status",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("invited_by_id", sa.Integer(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["invited_by_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tenant_invites_email", "tenant_invites", ["email"], unique=False
    )
    op.create_index(
        "ix_tenant_invites_status", "tenant_invites", ["status"], unique=False
    )
    op.create_index(
        "ix_tenant_invites_tenant_id",
        "tenant_invites",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_tenant_invites_token", "tenant_invites", ["token"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_tenant_invites_token", table_name="tenant_invites")
    op.drop_index("ix_tenant_invites_tenant_id", table_name="tenant_invites")
    op.drop_index("ix_tenant_invites_status", table_name="tenant_invites")
    op.drop_index("ix_tenant_invites_email", table_name="tenant_invites")
    op.drop_table("tenant_invites")
