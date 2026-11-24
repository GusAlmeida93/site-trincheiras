"""admin accounts: teacher users, their sessions, sign-in throttling

Revision ID: 30707a4dcde2
Revises: d52d49c4556c
Create Date: 2026-11-24 16:22:45.822543

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '30707a4dcde2'
down_revision: Union[str, None] = 'd52d49c4556c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('admin_users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('password_hash', sa.Text(), nullable=True),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('setup_token_hash', sa.String(length=64), nullable=True),
    sa.Column('setup_token_expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('password_changed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_admin_users')),
    sa.UniqueConstraint('email', name=op.f('uq_admin_users_email')),
    sa.UniqueConstraint('setup_token_hash', name=op.f('uq_admin_users_setup_token_hash'))
    )
    op.create_table('login_throttles',
    sa.Column('key', sa.String(length=254), nullable=False),
    sa.Column('failures', sa.Integer(), nullable=False),
    sa.Column('window_started_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('key', name=op.f('pk_login_throttles'))
    )
    op.create_table('admin_sessions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('admin_user_id', sa.Integer(), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['admin_user_id'], ['admin_users.id'], name=op.f('fk_admin_sessions_admin_user_id_admin_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_admin_sessions')),
    sa.UniqueConstraint('token_hash', name=op.f('uq_admin_sessions_token_hash'))
    )
    op.create_index(op.f('ix_admin_sessions_admin_user_id'), 'admin_sessions', ['admin_user_id'], unique=False)
    op.create_index(op.f('ix_admin_sessions_expires_at'), 'admin_sessions', ['expires_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_admin_sessions_expires_at'), table_name='admin_sessions')
    op.drop_index(op.f('ix_admin_sessions_admin_user_id'), table_name='admin_sessions')
    op.drop_table('admin_sessions')
    op.drop_table('login_throttles')
    op.drop_table('admin_users')
