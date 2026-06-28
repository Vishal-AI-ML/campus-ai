"""add extracurriculars (ECA module)

Revision ID: f1e2d3c4b5a6
Revises: d8f3a1c6b2e7
Create Date: 2026-06-28 05:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f1e2d3c4b5a6'
down_revision: Union[str, Sequence[str], None] = 'd8f3a1c6b2e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # `skill_status` already exists (created by the skills migration); reuse it
    # WITHOUT re-creating the type. `eca_category` is new and is created here.
    skill_status = postgresql.ENUM(
        'pending', 'verified', 'flagged', name='skill_status', create_type=False
    )
    eca_category = sa.Enum(
        'sports',
        'cultural',
        'technical',
        'volunteering',
        'leadership',
        'other',
        name='eca_category',
    )
    op.create_table(
        'extracurriculars',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('category', eca_category, nullable=False),
        sa.Column('organization', sa.String(length=150), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('evidence_url', sa.String(length=500), nullable=True),
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
        sa.ForeignKeyConstraint(['reviewed_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['student_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('student_id', 'title', name='uq_eca_student_title'),
    )
    op.create_index(
        op.f('ix_extracurriculars_category'),
        'extracurriculars',
        ['category'],
        unique=False,
    )
    op.create_index(
        op.f('ix_extracurriculars_status'),
        'extracurriculars',
        ['status'],
        unique=False,
    )
    op.create_index(
        op.f('ix_extracurriculars_student_id'),
        'extracurriculars',
        ['student_id'],
        unique=False,
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f('ix_extracurriculars_student_id'), table_name='extracurriculars'
    )
    op.drop_index(op.f('ix_extracurriculars_status'), table_name='extracurriculars')
    op.drop_index(
        op.f('ix_extracurriculars_category'), table_name='extracurriculars'
    )
    op.drop_table('extracurriculars')
    op.execute('DROP TYPE IF EXISTS eca_category')
    # ### end Alembic commands ###
