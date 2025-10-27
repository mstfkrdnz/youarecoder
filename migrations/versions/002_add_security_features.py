"""Add password security and login tracking

Revision ID: 002_security
Revises: 001_initial
Create Date: 2025-10-27 03:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_security'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade():
    # Add account security fields to users table
    op.add_column('users', sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('account_locked_until', sa.DateTime(), nullable=True))

    # Create login_attempts table
    op.create_table('login_attempts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=False),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('failure_reason', sa.String(length=100), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_login_attempts_email'), 'login_attempts', ['email'], unique=False)
    op.create_index(op.f('ix_login_attempts_timestamp'), 'login_attempts', ['timestamp'], unique=False)


def downgrade():
    # Drop login_attempts table
    op.drop_index(op.f('ix_login_attempts_timestamp'), table_name='login_attempts')
    op.drop_index(op.f('ix_login_attempts_email'), table_name='login_attempts')
    op.drop_table('login_attempts')

    # Remove account security fields from users table
    op.drop_column('users', 'account_locked_until')
    op.drop_column('users', 'failed_login_attempts')
