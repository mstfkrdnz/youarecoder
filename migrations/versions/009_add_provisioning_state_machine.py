"""Add provisioning state machine fields for step-by-step tracking

Revision ID: 009
Revises: 008
Create Date: 2025-11-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None

def upgrade():
    """Add state machine tracking fields to workspaces table."""

    # Add new columns for state machine
    op.add_column('workspaces', sa.Column('provisioning_state', sa.String(50), nullable=False, server_default='created'))
    op.add_column('workspaces', sa.Column('provisioning_step', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('workspaces', sa.Column('total_steps', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('workspaces', sa.Column('provisioning_steps', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('workspaces', sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'))
    op.add_column('workspaces', sa.Column('last_retry_at', sa.DateTime(), nullable=True))

    # Add manual approval fields
    op.add_column('workspaces', sa.Column('requires_manual_approval', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('workspaces', sa.Column('approved_by_user_id', sa.Integer(), nullable=True))
    op.add_column('workspaces', sa.Column('approved_at', sa.DateTime(), nullable=True))

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_workspace_approved_by',
        'workspaces', 'users',
        ['approved_by_user_id'], ['id'],
        ondelete='SET NULL'
    )

    # Add indexes for performance
    op.create_index('ix_workspaces_provisioning_state', 'workspaces', ['provisioning_state'])
    op.create_index(
        'ix_workspaces_requires_approval',
        'workspaces',
        ['requires_manual_approval'],
        postgresql_where=sa.text('requires_manual_approval = true')
    )

def downgrade():
    """Remove state machine tracking fields from workspaces table."""

    # Drop indexes
    op.drop_index('ix_workspaces_requires_approval', 'workspaces')
    op.drop_index('ix_workspaces_provisioning_state', 'workspaces')

    # Drop foreign key
    op.drop_constraint('fk_workspace_approved_by', 'workspaces', type_='foreignkey')

    # Drop columns
    op.drop_column('workspaces', 'approved_at')
    op.drop_column('workspaces', 'approved_by_user_id')
    op.drop_column('workspaces', 'requires_manual_approval')
    op.drop_column('workspaces', 'last_retry_at')
    op.drop_column('workspaces', 'max_retries')
    op.drop_column('workspaces', 'provisioning_steps')
    op.drop_column('workspaces', 'total_steps')
    op.drop_column('workspaces', 'provisioning_step')
    op.drop_column('workspaces', 'provisioning_state')
