-- Migration: Email Communication Tracking
-- Purpose: PayTR chargeback evidence - Email trail tracking
-- Date: 2025-10-28
-- Description: Add email_logs table for comprehensive email communication tracking

-- Create email_logs table
CREATE TABLE IF NOT EXISTS email_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),

    -- User and company tracking
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    company_id INTEGER REFERENCES companies(id) ON DELETE SET NULL,

    -- Email details
    email_type VARCHAR(50) NOT NULL,
    recipient_email VARCHAR(255) NOT NULL,
    subject TEXT,
    content_hash VARCHAR(64),  -- SHA-256 hash for verification

    -- Delivery tracking
    sent_at TIMESTAMP NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    delivery_status VARCHAR(20) DEFAULT 'sent',
    mailjet_message_id VARCHAR(100),
    opened_at TIMESTAMP,
    clicked_at TIMESTAMP
);

-- Create indexes for email_logs
CREATE INDEX IF NOT EXISTS idx_email_logs_user_id ON email_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_email_logs_company_id ON email_logs(company_id);
CREATE INDEX IF NOT EXISTS idx_email_logs_timestamp ON email_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_email_logs_email_type ON email_logs(email_type);
CREATE INDEX IF NOT EXISTS idx_email_logs_sent_at ON email_logs(sent_at DESC);

-- Add comments for documentation
COMMENT ON TABLE email_logs IS 'Track all email communications for PayTR chargeback evidence. Provides proof of communication timeline.';

COMMENT ON COLUMN email_logs.email_type IS 'Type: registration, payment_confirmation, workspace_created, password_reset, etc.';
COMMENT ON COLUMN email_logs.content_hash IS 'SHA-256 hash of email content for verification';
COMMENT ON COLUMN email_logs.delivery_status IS 'Status: sent, delivered, bounced, failed';
COMMENT ON COLUMN email_logs.mailjet_message_id IS 'Mailjet tracking ID for external verification';

-- Verification queries
-- Run these after migration to verify success:

-- SELECT COUNT(*) FROM email_logs;
-- SELECT * FROM pg_indexes WHERE tablename = 'email_logs';
