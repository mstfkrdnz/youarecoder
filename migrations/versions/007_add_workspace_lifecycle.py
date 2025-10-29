"""Add workspace lifecycle management fields

Revision ID: 007
Revises: 006
Create Date: 2025-10-29

Implements workspace lifecycle tracking with:
- is_running: Current operational status
- last_started_at, last_stopped_at, last_accessed_at: Activity timestamps
- auto_stop_hours: Automatic shutdown policy
- cpu_limit_percent, memory_limit_mb: Resource limits
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade():
    """Add workspace lifecycle management fields."""

    # Add lifecycle tracking columns
    op.add_column('workspaces',
        sa.Column('is_running', sa.Boolean(), nullable=False, server_default='false')
    )
    op.add_column('workspaces',
        sa.Column('last_started_at', sa.DateTime(), nullable=True)
    )
    op.add_column('workspaces',
        sa.Column('last_stopped_at', sa.DateTime(), nullable=True)
    )
    op.add_column('workspaces',
        sa.Column('last_accessed_at', sa.DateTime(), nullable=True)
    )

    # Add resource management columns
    op.add_column('workspaces',
        sa.Column('auto_stop_hours', sa.Integer(), nullable=False, server_default='0')
    )
    op.add_column('workspaces',
        sa.Column('cpu_limit_percent', sa.Integer(), nullable=False, server_default='100')
    )
    op.add_column('workspaces',
        sa.Column('memory_limit_mb', sa.Integer(), nullable=False, server_default='2048')
    )

    # Create indexes for lifecycle queries
    op.create_index(
        'ix_workspaces_is_running',
        'workspaces',
        ['is_running']
    )
    op.create_index(
        'ix_workspaces_last_accessed_at',
        'workspaces',
        ['last_accessed_at']
    )


def downgrade():
    """Remove workspace lifecycle management fields."""

    # Drop indexes
    op.drop_index('ix_workspaces_last_accessed_at', table_name='workspaces')
    op.drop_index('ix_workspaces_is_running', table_name='workspaces')

    # Drop columns
    op.drop_column('workspaces', 'memory_limit_mb')
    op.drop_column('workspaces', 'cpu_limit_percent')
    op.drop_column('workspaces', 'auto_stop_hours')
    op.drop_column('workspaces', 'last_accessed_at')
    op.drop_column('workspaces', 'last_stopped_at')
    op.drop_column('workspaces', 'last_started_at')
    op.drop_column('workspaces', 'is_running')
