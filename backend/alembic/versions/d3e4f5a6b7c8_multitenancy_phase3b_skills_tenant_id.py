"""multitenancy phase3b: skills.tenant_id (app-layer isolation pilot)

Revision ID: d3e4f5a6b7c8
Revises: 7a8b9c0d1e2f
Create Date: 2026-06-29

First data table to get a tenant_id (the pilot for Phase 3). Pattern, reused
for every other tenant-scoped table later:

  1) add the column NULLABLE so existing rows survive the migration,
  2) backfill each row from its owner's tenant (here: the skill's student),
  3) safety-net any leftover NULLs to the earliest tenant,
  4) add FK + index, then tighten to NOT NULL last.

This is the inverse order of a drop, so downgrade removes index/FK/column.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "d3e4f5a6b7c8"
down_revision = "7a8b9c0d1e2f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) Add nullable first so the existing skills rows don't violate NOT NULL
    #    mid-migration.
    op.add_column("skills", sa.Column("tenant_id", sa.Integer(), nullable=True))

    # 2) Backfill: every skill inherits its student's tenant.
    op.execute(
        "UPDATE skills SET tenant_id = "
        "(SELECT tenant_id FROM users WHERE users.id = skills.student_id) "
        "WHERE tenant_id IS NULL"
    )

    # 3) Safety net: any orphaned skill (no/!matching student) goes to the
    #    earliest tenant (the seeded default institute) so step 4 can't fail.
    op.execute(
        "UPDATE skills SET tenant_id = (SELECT id FROM tenants ORDER BY id LIMIT 1) "
        "WHERE tenant_id IS NULL"
    )

    # 4) Wire up FK + index, then enforce NOT NULL.
    op.create_foreign_key(
        "fk_skills_tenant_id",
        "skills",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_skills_tenant_id", "skills", ["tenant_id"])
    op.alter_column(
        "skills",
        "tenant_id",
        existing_type=sa.Integer(),
        nullable=False,
    )


def downgrade() -> None:
    op.drop_index("ix_skills_tenant_id", table_name="skills")
    op.drop_constraint("fk_skills_tenant_id", "skills", type_="foreignkey")
    op.drop_column("skills", "tenant_id")
