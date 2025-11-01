"""Add exchange rates table for dynamic currency conversion

Revision ID: 009_exchange_rates
Revises: 008_add_workspace_metrics
Create Date: 2025-11-01

This migration creates the exchange_rates table to store daily TCMB exchange rates
for dynamic multi-currency pricing (USD, EUR, TRY).
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers
revision = '009_exchange_rates'
down_revision = '008_add_workspace_metrics'
branch_labels = None
depends_on = None


def upgrade():
    """Create exchange_rates table."""
    op.create_table('exchange_rates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('target_currency', sa.String(length=3), nullable=False, server_default='TRY'),
        sa.Column('rate', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('effective_date', sa.Date(), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False, server_default='TCMB'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_currency', 'target_currency', 'effective_date',
                          name='uq_currency_date')
    )

    # Create index for fast date-based lookups
    op.create_index(
        'ix_exchange_rates_effective_date',
        'exchange_rates',
        ['effective_date'],
        unique=False
    )


def downgrade():
    """Drop exchange_rates table."""
    op.drop_index('ix_exchange_rates_effective_date', table_name='exchange_rates')
    op.drop_table('exchange_rates')
