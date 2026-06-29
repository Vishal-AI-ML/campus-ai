"""add internships (Internship/OJT module)

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-28 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # `skill_status` already exists (created by the skills migration); reuse it
    # WITHOUT re-creating the type. `internship_type` is new and created here.
    skill_status = postgresql.ENUM(
        'pending', 'verified', 'flagged', name='skill_status', create_type=False
    )
    internship_type = sa.Enum(
        'internship',
        'ojt',
        'apprenticeship',
        'training',
        'other',
        name='internship_type',
    )
    op.create_table(
        'internships',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('organization', sa.String(length=200), nullable=False),
        sa.Column('role_title', sa.String(length=150), nullable=False),
        sa.Column('internship_type', internship_type, nullable=False),
        sa.Column('mode', sa.String(length=20), nullable=True),
        sa.Column('location', sa.String(length=150), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('skills_used', sa.String(length=300), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('is_ongoing', sa.Boolean(), nullable=False),
        sa.Column('certificate_url', sa.String(length=500), nullable=True),
        sa.Column('status', skill_status, nullable=False),
        sa.Column('reviewed_by_id', sa.Integer(), nullable=True),
        sa.Column('review_note', sa.String(length=500), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ['reviewed_by_id'], ['users.id'], ondelete='SET NULL'
        ),
        sa.ForeignKeyConstraint(['student_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'student_id',
            'organization',
            'role_title',
            name='uq_internship_student_org_role',
        ),
    )
    op.create_index(
        op.f('ix_internships_internship_type'),
        'internships',
        ['internship_type'],
        unique=False,
    )
    op.create_index(
        op.f('ix_internships_status'),
        'internships',
        ['status'],
        unique=False,
    )
    op.create_index(
        op.f('ix_internships_student_id'),
        'internships',
        ['student_id'],
        unique=False,
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_internships_student_id'), table_name='internships')
    op.drop_index(op.f('ix_internships_status'), table_name='internships')
    op.drop_index(
        op.f('ix_internships_internship_type'), table_name='internships'
    )
    op.drop_table('internships')
    op.execute('DROP TYPE IF EXISTS internship_type')
    # ### end Alembic commands ###
