"""Add workspace metrics table for resource monitoring

Revision ID: 008
Revises: 007
Create Date: 2025-10-29

Implements workspace resource metrics tracking with:
- workspace_metrics table for time-series CPU/memory data
- Composite index for efficient time-range queries
- Foreign key cascade delete for workspace cleanup
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade():
    """Add workspace_metrics table."""

    # Create workspace_metrics table
    op.create_table(
        'workspace_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workspace_id', sa.Integer(), nullable=False),
        sa.Column('collected_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('cpu_percent', sa.Float(), nullable=False),
        sa.Column('memory_used_mb', sa.Integer(), nullable=False),
        sa.Column('memory_percent', sa.Float(), nullable=False),
        sa.Column('process_count', sa.Integer(), nullable=False),
        sa.Column('uptime_seconds', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Add foreign key to workspaces
    op.create_foreign_key(
        'fk_workspace_metrics_workspace_id',
        'workspace_metrics', 'workspaces',
        ['workspace_id'], ['id'],
        ondelete='CASCADE'
    )

    # Create indexes for efficient queries
    op.create_index(
        'ix_workspace_metrics_workspace_id',
        'workspace_metrics',
        ['workspace_id']
    )

    op.create_index(
        'ix_workspace_metrics_collected_at',
        'workspace_metrics',
        ['collected_at']
    )

    # Composite index for time-range queries per workspace
    op.create_index(
        'ix_workspace_metrics_workspace_time',
        'workspace_metrics',
        ['workspace_id', 'collected_at']
    )


def downgrade():
    """Remove workspace_metrics table."""

    # Drop indexes
    op.drop_index('ix_workspace_metrics_workspace_time', table_name='workspace_metrics')
    op.drop_index('ix_workspace_metrics_collected_at', table_name='workspace_metrics')
    op.drop_index('ix_workspace_metrics_workspace_id', table_name='workspace_metrics')

    # Drop foreign key
    op.drop_constraint('fk_workspace_metrics_workspace_id', 'workspace_metrics', type_='foreignkey')

    # Drop table
    op.drop_table('workspace_metrics')
