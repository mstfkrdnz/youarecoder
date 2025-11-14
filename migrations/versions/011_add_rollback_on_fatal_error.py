"""Add rollback_on_fatal_error to workspace templates

Revision ID: 011
Revises: 010
Create Date: 2025-11-09

Implements rollback configuration for workspace template action execution:
- rollback_on_fatal_error field in workspace_templates table
- Controls whether completed actions should be rolled back when a fatal error occurs
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade():
    """Add rollback_on_fatal_error column to workspace_templates table."""

    # Add rollback_on_fatal_error column
    op.add_column(
        'workspace_templates',
        sa.Column(
            'rollback_on_fatal_error',
            sa.Boolean(),
            nullable=False,
            server_default='false',
            comment='Enable rollback of completed actions when a fatal error occurs'
        )
    )

    # Add index for templates with rollback enabled (for monitoring/analytics)
    op.create_index(
        'ix_workspace_templates_rollback_enabled',
        'workspace_templates',
        ['rollback_on_fatal_error']
    )


def downgrade():
    """Remove rollback_on_fatal_error column from workspace_templates table."""

    # Drop index first
    op.drop_index(
        'ix_workspace_templates_rollback_enabled',
        table_name='workspace_templates'
    )

    # Drop column
    op.drop_column('workspace_templates', 'rollback_on_fatal_error')
