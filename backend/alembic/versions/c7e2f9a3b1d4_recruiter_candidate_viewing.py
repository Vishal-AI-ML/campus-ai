"""recruiter candidate viewing: link drives + contact reveal gate (Step 27.2)

Revision ID: c7e2f9a3b1d4
Revises: b9d4e7c1a2f5
Create Date: 2026-06-27

Adds:
  * drives.recruiter_id  - optional FK so a drive can be assigned to a
                           recruiting company (its HR can then see candidates)
  * applications.contact_revealed - privacy gate; a recruiter sees a
                           candidate's contact only after the TPO reveals it
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "c7e2f9a3b1d4"
down_revision = "b9d4e7c1a2f5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Link a drive to a recruiting company (nullable; SET NULL on delete).
    op.add_column(
        "drives",
        sa.Column("recruiter_id", sa.Integer(), nullable=True),
    )
    op.create_index("ix_drives_recruiter_id", "drives", ["recruiter_id"])
    op.create_foreign_key(
        "fk_drives_recruiter_id",
        "drives",
        "recruiters",
        ["recruiter_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Contact-reveal gate. Backfill existing rows to False via server_default,
    # then drop the default so the ORM owns it for new rows.
    op.add_column(
        "applications",
        sa.Column(
            "contact_revealed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.alter_column("applications", "contact_revealed", server_default=None)


def downgrade() -> None:
    op.drop_column("applications", "contact_revealed")
    op.drop_constraint("fk_drives_recruiter_id", "drives", type_="foreignkey")
    op.drop_index("ix_drives_recruiter_id", table_name="drives")
    op.drop_column("drives", "recruiter_id")
