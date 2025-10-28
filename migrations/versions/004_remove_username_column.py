"""Remove username column from users table

Revision ID: 004
Revises: 003
Create Date: 2025-10-28

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    """Remove username column and its index."""
    # Drop index first
    op.drop_index('ix_users_username', table_name='users')

    # Drop column
    op.drop_column('users', 'username')


def downgrade():
    """Restore username column and index."""
    # Add column back
    op.add_column('users',
        sa.Column('username', sa.String(length=50), nullable=True)
    )

    # Create index
    op.create_index('ix_users_username', 'users', ['username'], unique=True)

    # Note: Cannot restore original username data in downgrade
