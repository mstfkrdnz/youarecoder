-- Migration: Audit Trail and Usage Logs System
-- Purpose: PayTR USD/EUR compliance - Phase 2
-- Date: 2025-10-28
-- Description: Add audit_logs and workspace_sessions tables for comprehensive activity tracking

-- Create audit_logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),

    -- User and company tracking
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    company_id INTEGER REFERENCES companies(id) ON DELETE SET NULL,

    -- Action details
    action_type VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50),
    resource_id INTEGER,

    -- Request context
    ip_address VARCHAR(45),  -- IPv6 support
    user_agent TEXT,
    request_method VARCHAR(10),
    request_path VARCHAR(500),

    -- Additional details (flexible JSON storage)
    details JSONB,

    -- Result tracking
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT
);

-- Create indexes for audit_logs
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_company_id ON audit_logs(company_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action_type ON audit_logs(action_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource_type ON audit_logs(resource_type);

-- Create workspace_sessions table
CREATE TABLE IF NOT EXISTS workspace_sessions (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Session timing
    started_at TIMESTAMP NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    ended_at TIMESTAMP,
    duration_seconds INTEGER,

    -- Activity tracking
    last_activity_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    activity_count INTEGER DEFAULT 0,

    -- Request context
    ip_address VARCHAR(45),
    user_agent TEXT,
    session_id VARCHAR(100),
    access_method VARCHAR(20)  -- 'web', 'api', 'ssh'
);

-- Create indexes for workspace_sessions
CREATE INDEX IF NOT EXISTS idx_workspace_sessions_workspace_id ON workspace_sessions(workspace_id);
CREATE INDEX IF NOT EXISTS idx_workspace_sessions_user_id ON workspace_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_workspace_sessions_started_at ON workspace_sessions(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_workspace_sessions_session_id ON workspace_sessions(session_id);

-- Add comments for documentation
COMMENT ON TABLE audit_logs IS 'Comprehensive audit trail for all system activities. Used for PayTR chargeback evidence and compliance.';
COMMENT ON TABLE workspace_sessions IS 'Track workspace usage sessions for billing and compliance. Provides evidence of service delivery.';

COMMENT ON COLUMN audit_logs.id IS 'BigInteger primary key for high-volume logging';
COMMENT ON COLUMN audit_logs.timestamp IS 'UTC timestamp of action, indexed for fast queries';
COMMENT ON COLUMN audit_logs.action_type IS 'Type of action: login, logout, payment_initiated, workspace_create, etc.';
COMMENT ON COLUMN audit_logs.details IS 'Flexible JSONB storage for action-specific data';
COMMENT ON COLUMN audit_logs.success IS 'Whether action succeeded. False indicates errors.';

COMMENT ON COLUMN workspace_sessions.duration_seconds IS 'Calculated duration when session ends';
COMMENT ON COLUMN workspace_sessions.activity_count IS 'Number of activities during session (file edits, etc.)';
COMMENT ON COLUMN workspace_sessions.access_method IS 'How workspace was accessed: web, api, ssh';

-- Verification queries
-- Run these after migration to verify success:

-- SELECT COUNT(*) FROM audit_logs;
-- SELECT COUNT(*) FROM workspace_sessions;
-- SELECT * FROM pg_indexes WHERE tablename IN ('audit_logs', 'workspace_sessions');
