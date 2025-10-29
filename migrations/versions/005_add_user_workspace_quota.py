"""Add workspace quota fields to users table

Revision ID: 005
Revises: 004
Create Date: 2025-10-29

Implements per-developer workspace quota system with:
- workspace_quota: Maximum workspaces a user can create
- quota_assigned_at: Timestamp when quota was last assigned
- quota_assigned_by: Reference to admin who assigned the quota

Initialization logic distributes company max_workspaces equally among existing users.
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    """Add workspace quota fields and initialize values."""
    # Add columns
    op.add_column('users',
        sa.Column('workspace_quota', sa.Integer(), nullable=False, server_default='1')
    )
    op.add_column('users',
        sa.Column('quota_assigned_at', sa.DateTime(), nullable=True)
    )
    op.add_column('users',
        sa.Column('quota_assigned_by', sa.Integer(), nullable=True)
    )

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_users_quota_assigned_by',
        'users', 'users',
        ['quota_assigned_by'], ['id'],
        ondelete='SET NULL'
    )

    # Initialize quotas: equal distribution of company max_workspaces
    connection = op.get_bind()

    # Get all companies
    companies = connection.execute(
        sa.text("SELECT id, max_workspaces FROM companies")
    ).fetchall()

    for company_id, max_workspaces in companies:
        # Count non-admin users (members who will get quotas)
        user_count_result = connection.execute(
            sa.text("SELECT COUNT(*) FROM users WHERE company_id = :company_id AND role != 'admin'"),
            {"company_id": company_id}
        ).fetchone()
        user_count = user_count_result[0] if user_count_result else 0

        if user_count > 0:
            # Distribute company quota equally among users
            quota_per_user = max(1, max_workspaces // user_count)

            # Update all non-admin users with their quota
            connection.execute(
                sa.text("""
                    UPDATE users
                    SET workspace_quota = :quota,
                        quota_assigned_at = :assigned_at
                    WHERE company_id = :company_id
                    AND role != 'admin'
                """),
                {
                    "quota": quota_per_user,
                    "assigned_at": datetime.utcnow(),
                    "company_id": company_id
                }
            )

    connection.commit()


def downgrade():
    """Remove workspace quota fields."""
    op.drop_constraint('fk_users_quota_assigned_by', 'users', type_='foreignkey')
    op.drop_column('users', 'quota_assigned_by')
    op.drop_column('users', 'quota_assigned_at')
    op.drop_column('users', 'workspace_quota')
