"""Add Odoo-specific workspace fields

Revision ID: 010
Revises: 009
Create Date: 2025-11-06
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade():
    """Add Odoo provisioning tracking fields to workspaces table."""

    # Port management
    op.add_column('workspaces', sa.Column('odoo_port', sa.Integer(), nullable=True))

    # Database tracking
    op.add_column('workspaces', sa.Column('db_name', sa.String(255), nullable=True))

    # Provisioning progress tracking
    op.add_column('workspaces', sa.Column('venv_created', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('workspaces', sa.Column('requirements_installed', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('workspaces', sa.Column('database_initialized', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('workspaces', sa.Column('odoo_config_generated', sa.Boolean(), nullable=False, server_default='false'))

    # Add index for database name lookups
    op.create_index('ix_workspaces_db_name', 'workspaces', ['db_name'])


def downgrade():
    """Remove Odoo-specific fields from workspaces table."""

    op.drop_index('ix_workspaces_db_name', 'workspaces')
    op.drop_column('workspaces', 'odoo_config_generated')
    op.drop_column('workspaces', 'database_initialized')
    op.drop_column('workspaces', 'requirements_installed')
    op.drop_column('workspaces', 'venv_created')
    op.drop_column('workspaces', 'db_name')
    op.drop_column('workspaces', 'odoo_port')
