"""recruiter portal tables + recruiter role

Revision ID: b9d4e7c1a2f5
Revises: 2d2fd7f1d652
Create Date: 2026-06-27 16:10:00.000000

Adds the first external-facing role and its tables:
  * extends the user_role enum with 'recruiter'
  * recruiters         - a recruiting company onboarded by the TPO
  * recruiter_users    - links a login account to its company (multi-HR ready)
  * recruiter_invites  - single-use invite tokens the TPO sends to recruiters
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b9d4e7c1a2f5'
down_revision: Union[str, Sequence[str], None] = '2d2fd7f1d652'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Extend the existing user_role enum with the new external role.
    # (PG 12+ allows ADD VALUE inside a transaction; we never use it in this
    # same migration, so this is safe.)
    op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'recruiter'")

    op.create_table(
        'recruiters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_name', sa.String(length=200), nullable=False),
        sa.Column('website', sa.String(length=300), nullable=True),
        sa.Column('about', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('pending', 'active', 'suspended', name='recruiter_status'), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_recruiters_company_name'), 'recruiters', ['company_name'], unique=False)
    op.create_index(op.f('ix_recruiters_status'), 'recruiters', ['status'], unique=False)

    op.create_table(
        'recruiter_users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recruiter_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=150), nullable=True),
        sa.Column('is_primary', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['recruiter_id'], ['recruiters.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', name='uq_recruiter_user_account'),
    )
    op.create_index(op.f('ix_recruiter_users_recruiter_id'), 'recruiter_users', ['recruiter_id'], unique=False)
    op.create_index(op.f('ix_recruiter_users_user_id'), 'recruiter_users', ['user_id'], unique=False)

    op.create_table(
        'recruiter_invites',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recruiter_id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('token', sa.String(length=64), nullable=False),
        sa.Column('status', sa.Enum('pending', 'accepted', 'revoked', 'expired', name='invite_status'), nullable=False),
        sa.Column('title', sa.String(length=150), nullable=True),
        sa.Column('invited_by_id', sa.Integer(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['invited_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['recruiter_id'], ['recruiters.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_recruiter_invites_email'), 'recruiter_invites', ['email'], unique=False)
    op.create_index(op.f('ix_recruiter_invites_recruiter_id'), 'recruiter_invites', ['recruiter_id'], unique=False)
    op.create_index(op.f('ix_recruiter_invites_status'), 'recruiter_invites', ['status'], unique=False)
    op.create_index(op.f('ix_recruiter_invites_token'), 'recruiter_invites', ['token'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_recruiter_invites_token'), table_name='recruiter_invites')
    op.drop_index(op.f('ix_recruiter_invites_status'), table_name='recruiter_invites')
    op.drop_index(op.f('ix_recruiter_invites_recruiter_id'), table_name='recruiter_invites')
    op.drop_index(op.f('ix_recruiter_invites_email'), table_name='recruiter_invites')
    op.drop_table('recruiter_invites')

    op.drop_index(op.f('ix_recruiter_users_user_id'), table_name='recruiter_users')
    op.drop_index(op.f('ix_recruiter_users_recruiter_id'), table_name='recruiter_users')
    op.drop_table('recruiter_users')

    op.drop_index(op.f('ix_recruiters_status'), table_name='recruiters')
    op.drop_index(op.f('ix_recruiters_company_name'), table_name='recruiters')
    op.drop_table('recruiters')

    op.execute('DROP TYPE IF EXISTS invite_status')
    op.execute('DROP TYPE IF EXISTS recruiter_status')
    # Note: the 'recruiter' value on user_role is intentionally left in place
    # (PostgreSQL cannot drop a single enum value safely).
