"""recruiter decisions + offers (Step 27.3)

Adds the recruiter's non-binding decision fields to `applications` and a new
`offers` table (one offer per application) for formal offers a recruiter
extends to a candidate and the student then accepts/declines.

Enum handling (important): the two enum TYPES are created explicitly up front
with `checkfirst=True`, and every column references them with
`create_type=False`. This avoids both failure modes:
  * double-create -> "type already exists" (if the column also tried to create)
  * no-create     -> "type does not exist" (ADD COLUMN does not auto-create)

Revision ID: d8f3a1c6b2e7
Revises: c7e2f9a3b1d4
Create Date: 2026-06-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d8f3a1c6b2e7"
down_revision: Union[str, Sequence[str], None] = "c7e2f9a3b1d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# create_type=False -> these objects never auto-emit CREATE TYPE in DDL;
# we create/drop them explicitly below.
recruiter_decision = postgresql.ENUM(
    "pending",
    "interested",
    "on_hold",
    "rejected",
    name="recruiter_decision",
    create_type=False,
)
offer_status = postgresql.ENUM(
    "extended",
    "accepted",
    "declined",
    "withdrawn",
    name="offer_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()

    # 1) Create the enum types explicitly (idempotent).
    recruiter_decision.create(bind, checkfirst=True)
    offer_status.create(bind, checkfirst=True)

    # 2) applications: recruiter's non-binding decision.
    op.add_column(
        "applications",
        sa.Column(
            "recruiter_decision",
            recruiter_decision,
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "applications",
        sa.Column("recruiter_decision_note", sa.Text(), nullable=True),
    )
    op.add_column(
        "applications",
        sa.Column(
            "recruiter_decided_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    # Drop the backfill default; the ORM supplies it going forward.
    op.alter_column("applications", "recruiter_decision", server_default=None)

    # 3) offers table.
    op.create_table(
        "offers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("recruiter_id", sa.Integer(), nullable=False),
        sa.Column("drive_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("role_title", sa.String(length=200), nullable=False),
        sa.Column("package_lpa", sa.Float(), nullable=True),
        sa.Column("location", sa.String(length=150), nullable=True),
        sa.Column("joining_date", sa.Date(), nullable=True),
        sa.Column("expires_on", sa.Date(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "status",
            offer_status,
            nullable=False,
            server_default="extended",
        ),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("student_response_note", sa.Text(), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["application_id"], ["applications.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["recruiter_id"], ["recruiters.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["drive_id"], ["drives.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["student_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("application_id", name="uq_offer_application"),
    )
    op.create_index("ix_offers_recruiter_id", "offers", ["recruiter_id"])
    op.create_index("ix_offers_drive_id", "offers", ["drive_id"])
    op.create_index("ix_offers_student_id", "offers", ["student_id"])
    op.create_index("ix_offers_status", "offers", ["status"])
    # Drop the backfill default; the ORM supplies it going forward.
    op.alter_column("offers", "status", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index("ix_offers_status", table_name="offers")
    op.drop_index("ix_offers_student_id", table_name="offers")
    op.drop_index("ix_offers_drive_id", table_name="offers")
    op.drop_index("ix_offers_recruiter_id", table_name="offers")
    op.drop_table("offers")

    op.drop_column("applications", "recruiter_decided_at")
    op.drop_column("applications", "recruiter_decision_note")
    op.drop_column("applications", "recruiter_decision")

    # Enum types are not auto-dropped by drop_table/drop_column.
    offer_status.drop(bind, checkfirst=True)
    recruiter_decision.drop(bind, checkfirst=True)
