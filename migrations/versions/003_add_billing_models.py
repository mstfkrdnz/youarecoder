"""Add subscription, payment, and invoice models for PayTR integration

Revision ID: 003_billing
Revises: 002_security
Create Date: 2025-10-27 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003_billing'
down_revision = '002_security'
branch_labels = None
depends_on = None


def upgrade():
    # Create subscriptions table
    op.create_table('subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('plan', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='trial'),
        sa.Column('trial_starts_at', sa.DateTime(), nullable=True),
        sa.Column('trial_ends_at', sa.DateTime(), nullable=True),
        sa.Column('current_period_start', sa.DateTime(), nullable=True),
        sa.Column('current_period_end', sa.DateTime(), nullable=True),
        sa.Column('paytr_subscription_id', sa.String(length=100), nullable=True),
        sa.Column('cancel_at_period_end', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('cancelled_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_id'),
        sa.UniqueConstraint('paytr_subscription_id')
    )
    op.create_index(op.f('ix_subscriptions_company_id'), 'subscriptions', ['company_id'], unique=True)
    op.create_index(op.f('ix_subscriptions_paytr_subscription_id'), 'subscriptions', ['paytr_subscription_id'], unique=True)

    # Create payments table
    op.create_table('payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=True),
        sa.Column('paytr_merchant_oid', sa.String(length=100), nullable=False),
        sa.Column('paytr_transaction_id', sa.String(length=100), nullable=True),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('payment_type', sa.String(length=20), nullable=False),
        sa.Column('failure_reason_code', sa.String(length=50), nullable=True),
        sa.Column('failure_reason_message', sa.String(length=255), nullable=True),
        sa.Column('test_mode', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('user_ip', sa.String(length=45), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('paytr_merchant_oid')
    )
    op.create_index(op.f('ix_payments_company_id'), 'payments', ['company_id'], unique=False)
    op.create_index(op.f('ix_payments_subscription_id'), 'payments', ['subscription_id'], unique=False)
    op.create_index(op.f('ix_payments_paytr_merchant_oid'), 'payments', ['paytr_merchant_oid'], unique=True)
    op.create_index(op.f('ix_payments_paytr_transaction_id'), 'payments', ['paytr_transaction_id'], unique=False)

    # Create invoices table
    op.create_table('invoices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('payment_id', sa.Integer(), nullable=True),
        sa.Column('invoice_number', sa.String(length=50), nullable=False),
        sa.Column('subtotal', sa.Integer(), nullable=False),
        sa.Column('tax_amount', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_amount', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('invoice_date', sa.DateTime(), nullable=False),
        sa.Column('due_date', sa.DateTime(), nullable=False),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('invoice_number'),
        sa.UniqueConstraint('payment_id')
    )
    op.create_index(op.f('ix_invoices_company_id'), 'invoices', ['company_id'], unique=False)
    op.create_index(op.f('ix_invoices_payment_id'), 'invoices', ['payment_id'], unique=True)
    op.create_index(op.f('ix_invoices_invoice_number'), 'invoices', ['invoice_number'], unique=True)


def downgrade():
    # Drop invoices table
    op.drop_index(op.f('ix_invoices_invoice_number'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_payment_id'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_company_id'), table_name='invoices')
    op.drop_table('invoices')

    # Drop payments table
    op.drop_index(op.f('ix_payments_paytr_transaction_id'), table_name='payments')
    op.drop_index(op.f('ix_payments_paytr_merchant_oid'), table_name='payments')
    op.drop_index(op.f('ix_payments_subscription_id'), table_name='payments')
    op.drop_index(op.f('ix_payments_company_id'), table_name='payments')
    op.drop_table('payments')

    # Drop subscriptions table
    op.drop_index(op.f('ix_subscriptions_paytr_subscription_id'), table_name='subscriptions')
    op.drop_index(op.f('ix_subscriptions_company_id'), table_name='subscriptions')
    op.drop_table('subscriptions')
