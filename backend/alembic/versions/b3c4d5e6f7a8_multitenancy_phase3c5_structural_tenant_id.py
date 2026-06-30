"""multitenancy phase3c batch5: tenant_id on structural tables

Revision ID: b3c4d5e6f7a8
Revises: a8b9c0d1e2f3
Create Date: 2026-06-30

Batch 5 of Phase 3c. The *structural* academic tables: departments, sections
and subjects.

The twist this batch: `departments.name` and `departments.code` were GLOBALLY
unique. In a multi-tenant world that's wrong - two institutes must each be
allowed their own 'Computer Science' / 'CSE'. So we also swap those global
unique constraints for per-tenant ones (tenant_id + name, tenant_id + code).

Tenant inheritance:
  * departments -> no creator FK (they predate tenants) -> earliest tenant
  * sections    -> from their parent department
  * subjects    -> from their parent department

Department uniqueness is the only constraint surgery; sections
(uq department_id+name) and subjects (uq department_id+code) are already
department-scoped, so once the department is tenant-bound they're safe as-is.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "b3c4d5e6f7a8"
down_revision = "a8b9c0d1e2f3"
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


def _drop_single_col_unique(table: str, column: str) -> None:
    """Drop the single-column UNIQUE on (column), whether Postgres backs it
    with a named unique CONSTRAINT or a unique INDEX.

    `departments.name` was declared `unique=True` -> a unique constraint
    (e.g. departments_name_key), while `departments.code` was
    `unique=True, index=True` -> a unique *index* (e.g. ix_departments_code).
    Rather than hard-code those names, we introspect and drop whichever exists.
    """
    insp = sa.inspect(op.get_bind())
    for uc in insp.get_unique_constraints(table):
        if uc["column_names"] == [column]:
            op.drop_constraint(uc["name"], table, type_="unique")
            return
    for ix in insp.get_indexes(table):
        if ix.get("unique") and ix["column_names"] == [column]:
            op.drop_index(ix["name"], table_name=table)
            return


def upgrade() -> None:
    # --- departments: backfill to earliest tenant, swap unique constraints ---
    _add_tenant_column("departments")
    op.execute(
        f"UPDATE departments SET tenant_id = {_EARLIEST_TENANT} "
        f"WHERE tenant_id IS NULL"
    )
    # Global uniqueness -> per-tenant uniqueness. The backing objects differ
    # (name = unique constraint, code = unique index), so drop by introspection.
    _drop_single_col_unique("departments", "name")
    _drop_single_col_unique("departments", "code")
    op.create_unique_constraint(
        "uq_department_tenant_name", "departments", ["tenant_id", "name"]
    )
    op.create_unique_constraint(
        "uq_department_tenant_code", "departments", ["tenant_id", "code"]
    )
    op.alter_column(
        "departments", "tenant_id", existing_type=sa.Integer(), nullable=False
    )

    # --- sections: inherit tenant from their department ---
    _add_tenant_column("sections")
    op.execute(
        "UPDATE sections SET tenant_id = "
        "(SELECT tenant_id FROM departments WHERE departments.id = "
        "sections.department_id) WHERE tenant_id IS NULL"
    )
    op.execute(
        f"UPDATE sections SET tenant_id = {_EARLIEST_TENANT} "
        f"WHERE tenant_id IS NULL"
    )
    op.alter_column(
        "sections", "tenant_id", existing_type=sa.Integer(), nullable=False
    )

    # --- subjects: inherit tenant from their department ---
    _add_tenant_column("subjects")
    op.execute(
        "UPDATE subjects SET tenant_id = "
        "(SELECT tenant_id FROM departments WHERE departments.id = "
        "subjects.department_id) WHERE tenant_id IS NULL"
    )
    op.execute(
        f"UPDATE subjects SET tenant_id = {_EARLIEST_TENANT} "
        f"WHERE tenant_id IS NULL"
    )
    op.alter_column(
        "subjects", "tenant_id", existing_type=sa.Integer(), nullable=False
    )


def downgrade() -> None:
    # subjects
    op.drop_index("ix_subjects_tenant_id", table_name="subjects")
    op.drop_constraint("fk_subjects_tenant_id", "subjects", type_="foreignkey")
    op.drop_column("subjects", "tenant_id")

    # sections
    op.drop_index("ix_sections_tenant_id", table_name="sections")
    op.drop_constraint("fk_sections_tenant_id", "sections", type_="foreignkey")
    op.drop_column("sections", "tenant_id")

    # departments: restore global unique constraints
    op.drop_constraint(
        "uq_department_tenant_name", "departments", type_="unique"
    )
    op.drop_constraint(
        "uq_department_tenant_code", "departments", type_="unique"
    )
    op.create_unique_constraint(
        "departments_name_key", "departments", ["name"]
    )
    # `code` was originally a unique INDEX, not a constraint - restore as such.
    op.create_index(
        "ix_departments_code", "departments", ["code"], unique=True
    )
    op.drop_index("ix_departments_tenant_id", table_name="departments")
    op.drop_constraint(
        "fk_departments_tenant_id", "departments", type_="foreignkey"
    )
    op.drop_column("departments", "tenant_id")
