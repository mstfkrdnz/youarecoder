"""
Database models for YouAreCoder platform.
"""
from datetime import datetime, timedelta
from flask_login import UserMixin
from app import db, bcrypt


class Company(db.Model):
    """Company model for multi-tenant organization."""
    __tablename__ = 'companies'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    subdomain = db.Column(db.String(50), nullable=False, unique=True, index=True)
    plan = db.Column(db.String(20), nullable=False, default='starter')  # starter, team, enterprise
    status = db.Column(db.String(20), nullable=False, default='active')  # active, suspended, cancelled
    max_workspaces = db.Column(db.Integer, nullable=False, default=1)
    preferred_currency = db.Column(db.String(3), nullable=False, default='TRY')  # TRY, USD, EUR
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    users = db.relationship('User', backref='company', lazy='dynamic', cascade='all, delete-orphan')
    workspaces = db.relationship('Workspace', backref='company', lazy='dynamic', cascade='all, delete-orphan')
    subscription = db.relationship('Subscription', backref='company', uselist=False, cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='company', lazy='dynamic', cascade='all, delete-orphan')
    invoices = db.relationship('Invoice', backref='company', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Company {self.name} ({self.subdomain})>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'subdomain': self.subdomain,
            'plan': self.plan,
            'status': self.status,
            'max_workspaces': self.max_workspaces,
            'workspace_count': self.workspaces.count(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    def can_create_workspace(self):
        """Check if company can create more workspaces."""
        return self.workspaces.count() < self.max_workspaces

    def is_trial(self):
        """Check if company is currently in trial period."""
        if not self.subscription:
            return False
        return self.subscription.status == 'trial' and self.subscription.trial_ends_at and self.subscription.trial_ends_at > datetime.utcnow()

    def subscription_active(self):
        """Check if company has active subscription (trial or paid)."""
        if not self.subscription:
            return False
        return self.subscription.status in ['trial', 'active']

    def trial_days_remaining(self):
        """Get number of trial days remaining."""
        if not self.is_trial() or not self.subscription.trial_ends_at:
            return 0
        delta = self.subscription.trial_ends_at - datetime.utcnow()
        return max(0, delta.days)


class User(UserMixin, db.Model):
    """User model with Flask-Login integration."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='member')  # admin, member
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Account security
    failed_login_attempts = db.Column(db.Integer, nullable=False, default=0)
    account_locked_until = db.Column(db.DateTime)

    # Legal acceptance tracking
    terms_accepted = db.Column(db.Boolean, nullable=False, default=False)
    terms_accepted_at = db.Column(db.DateTime)
    terms_accepted_ip = db.Column(db.String(45))  # IPv6 support
    terms_version = db.Column(db.String(20))  # e.g., "1.0", "2.0"

    privacy_accepted = db.Column(db.Boolean, nullable=False, default=False)
    privacy_accepted_at = db.Column(db.DateTime)
    privacy_accepted_ip = db.Column(db.String(45))
    privacy_version = db.Column(db.String(20))

    # Relationships
    workspaces = db.relationship('Workspace', backref='owner', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.email}>'

    def set_password(self, password):
        """Hash and set user password."""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        """Verify password against stored hash."""
        return bcrypt.check_password_hash(self.password_hash, password)

    def is_admin(self):
        """Check if user has admin role."""
        return self.role == 'admin'

    def is_account_locked(self):
        """Check if account is currently locked due to failed login attempts."""
        if self.account_locked_until is None:
            return False
        return datetime.utcnow() < self.account_locked_until

    def record_failed_login(self):
        """Record a failed login attempt and lock account if threshold exceeded."""
        self.failed_login_attempts += 1

        # Lock account for 30 minutes after 5 failed attempts
        if self.failed_login_attempts >= 5:
            from datetime import timedelta
            self.account_locked_until = datetime.utcnow() + timedelta(minutes=30)

    def reset_failed_logins(self):
        """Reset failed login attempts and unlock account."""
        self.failed_login_attempts = 0
        self.account_locked_until = None

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role,
            'is_active': self.is_active,
            'company_id': self.company_id,
            'workspace_count': self.workspaces.count(),
            'created_at': self.created_at.isoformat(),
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


class Workspace(db.Model):
    """Workspace model for code-server instances."""
    __tablename__ = 'workspaces'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    subdomain = db.Column(db.String(50), nullable=False, unique=True, index=True)
    linux_username = db.Column(db.String(50), nullable=False, unique=True)
    port = db.Column(db.Integer, nullable=False, unique=True)
    code_server_password = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, active, suspended, failed
    disk_quota_gb = db.Column(db.Integer, nullable=False, default=10)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('workspace_templates.id'), nullable=True)
    template_applied_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Lifecycle management fields (Phase 4)
    is_running = db.Column(db.Boolean, nullable=False, default=False)
    last_started_at = db.Column(db.DateTime)
    last_stopped_at = db.Column(db.DateTime)
    last_accessed_at = db.Column(db.DateTime)
    auto_stop_hours = db.Column(db.Integer, default=0)  # 0 = never auto-stop
    cpu_limit_percent = db.Column(db.Integer, default=100)
    memory_limit_mb = db.Column(db.Integer, default=2048)

    # Composite unique constraint for name within company
    __table_args__ = (
        db.UniqueConstraint('company_id', 'name', name='uq_company_workspace_name'),
    )

    def __repr__(self):
        return f'<Workspace {self.name} ({self.subdomain})>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'subdomain': self.subdomain,
            'linux_username': self.linux_username,
            'port': self.port,
            'status': self.status,
            'disk_quota_gb': self.disk_quota_gb,
            'company_id': self.company_id,
            'owner_id': self.owner_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    def get_url(self):
        """Get full workspace URL."""
        return f"https://{self.subdomain}.youarecoder.com"


class LoginAttempt(db.Model):
    """Login attempt tracking for security auditing."""
    __tablename__ = 'login_attempts'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False, index=True)
    ip_address = db.Column(db.String(45), nullable=False)  # IPv6 max length
    user_agent = db.Column(db.String(255))
    success = db.Column(db.Boolean, nullable=False)
    failure_reason = db.Column(db.String(100))  # invalid_password, account_locked, inactive_account
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f'<LoginAttempt {self.email} {"success" if self.success else "failed"} at {self.timestamp}>'

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'ip_address': self.ip_address,
            'success': self.success,
            'failure_reason': self.failure_reason,
            'timestamp': self.timestamp.isoformat()
        }


class Subscription(db.Model):
    """Subscription model for tracking company billing periods and trial status."""
    __tablename__ = 'subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, unique=True, index=True)
    plan = db.Column(db.String(20), nullable=False)  # starter, team, enterprise
    status = db.Column(db.String(20), nullable=False, default='trial')  # trial, active, past_due, cancelled, suspended

    # Trial period tracking
    trial_starts_at = db.Column(db.DateTime)
    trial_ends_at = db.Column(db.DateTime)

    # Billing period tracking
    current_period_start = db.Column(db.DateTime)
    current_period_end = db.Column(db.DateTime)

    # PayTR integration
    paytr_subscription_id = db.Column(db.String(100), unique=True, index=True)

    # Cancellation tracking
    cancel_at_period_end = db.Column(db.Boolean, nullable=False, default=False)
    cancelled_at = db.Column(db.DateTime)

    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Subscription company_id={self.company_id} plan={self.plan} status={self.status}>'

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'plan': self.plan,
            'status': self.status,
            'trial_starts_at': self.trial_starts_at.isoformat() if self.trial_starts_at else None,
            'trial_ends_at': self.trial_ends_at.isoformat() if self.trial_ends_at else None,
            'current_period_start': self.current_period_start.isoformat() if self.current_period_start else None,
            'current_period_end': self.current_period_end.isoformat() if self.current_period_end else None,
            'cancel_at_period_end': self.cancel_at_period_end,
            'cancelled_at': self.cancelled_at.isoformat() if self.cancelled_at else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    def is_active(self):
        """Check if subscription is currently active (trial or paid)."""
        return self.status in ['trial', 'active']

    def is_trial_expired(self):
        """Check if trial period has expired."""
        if self.status != 'trial' or not self.trial_ends_at:
            return False
        return datetime.utcnow() > self.trial_ends_at

    def days_until_renewal(self):
        """Get days until next billing period."""
        if not self.current_period_end:
            return None
        delta = self.current_period_end - datetime.utcnow()
        return max(0, delta.days)


class Payment(db.Model):
    """Payment model for tracking individual payment transactions via PayTR."""
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, index=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscriptions.id'), index=True)

    # PayTR transaction details
    paytr_merchant_oid = db.Column(db.String(100), unique=True, nullable=False, index=True)  # Unique order ID
    paytr_transaction_id = db.Column(db.String(100), index=True)  # PayTR's internal transaction ID

    # Payment details
    amount = db.Column(db.Integer, nullable=False)  # Amount in cents (e.g., 2900 = $29.00)
    currency = db.Column(db.String(3), nullable=False, default='USD')  # USD or TRY
    plan = db.Column(db.String(20))  # starter, team, enterprise - for callback processing
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, success, failed, refunded
    payment_type = db.Column(db.String(20), nullable=False)  # initial, recurring, one_time

    # Failure tracking
    failure_reason_code = db.Column(db.String(50))
    failure_reason_message = db.Column(db.String(255))

    # Test mode indicator
    test_mode = db.Column(db.Boolean, nullable=False, default=True)

    # User information
    user_ip = db.Column(db.String(45))

    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)  # When payment was successfully processed
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    invoice = db.relationship('Invoice', backref='payment', uselist=False, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Payment {self.paytr_merchant_oid} status={self.status} amount={self.amount/100:.2f} {self.currency}>'

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'subscription_id': self.subscription_id,
            'paytr_merchant_oid': self.paytr_merchant_oid,
            'amount': self.amount,
            'currency': self.currency,
            'status': self.status,
            'payment_type': self.payment_type,
            'test_mode': self.test_mode,
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

    def amount_display(self):
        """Get formatted amount for display."""
        symbol = '$' if self.currency == 'USD' else '₺'
        return f"{symbol}{self.amount / 100:.2f}"


class Invoice(db.Model):
    """Invoice model for billing records and receipts."""
    __tablename__ = 'invoices'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, index=True)
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.id'), unique=True, index=True)

    # Invoice details
    invoice_number = db.Column(db.String(50), unique=True, nullable=False, index=True)  # e.g., INV-2024-00001

    # Amounts (in cents)
    subtotal = db.Column(db.Integer, nullable=False)
    tax_amount = db.Column(db.Integer, nullable=False, default=0)
    total_amount = db.Column(db.Integer, nullable=False)
    currency = db.Column(db.String(3), nullable=False, default='USD')

    # Invoice period
    period_start = db.Column(db.DateTime, nullable=False)
    period_end = db.Column(db.DateTime, nullable=False)

    # Dates
    invoice_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    due_date = db.Column(db.DateTime, nullable=False)
    paid_at = db.Column(db.DateTime)

    # Status
    status = db.Column(db.String(20), nullable=False, default='draft')  # draft, sent, paid, void

    # Additional details
    description = db.Column(db.Text)
    notes = db.Column(db.Text)

    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Invoice {self.invoice_number} total={self.total_amount/100:.2f} {self.currency} status={self.status}>'

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'payment_id': self.payment_id,
            'invoice_number': self.invoice_number,
            'subtotal': self.subtotal,
            'tax_amount': self.tax_amount,
            'total_amount': self.total_amount,
            'currency': self.currency,
            'period_start': self.period_start.isoformat(),
            'period_end': self.period_end.isoformat(),
            'invoice_date': self.invoice_date.isoformat(),
            'due_date': self.due_date.isoformat(),
            'paid_at': self.paid_at.isoformat() if self.paid_at else None,
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }

    def generate_invoice_number(self):
        """Generate unique invoice number in format INV-YYYY-NNNNN."""
        year = datetime.utcnow().year
        # Get count of invoices this year
        count = db.session.query(Invoice).filter(
            Invoice.invoice_number.like(f'INV-{year}-%')
        ).count()
        return f'INV-{year}-{count + 1:05d}'

    @property
    def amount_display(self):
        """Get formatted amount for display (alias for total_display)."""
        return self.total_display()

    def total_display(self):
        """Get formatted total for display."""
        symbol = '$' if self.currency == 'USD' else '₺'
        return f"{symbol}{self.total_amount / 100:.2f}"


class AuditLog(db.Model):
    """
    Audit log for tracking all system activities.

    Purpose: PayTR USD/EUR compliance - provide evidence for chargeback disputes.
    Tracks: login, workspace access, payments, subscription changes, etc.
    """
    __tablename__ = 'audit_logs'

    id = db.Column(db.BigInteger, primary_key=True)  # BigInteger for high volume
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    # User and company tracking
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), index=True)

    # Action details
    action_type = db.Column(db.String(50), nullable=False, index=True)  # 'login', 'workspace_create', 'payment_success', etc.
    resource_type = db.Column(db.String(50), index=True)  # 'workspace', 'subscription', 'payment', etc.
    resource_id = db.Column(db.Integer)

    # Request context
    ip_address = db.Column(db.String(45))  # IPv6 support
    user_agent = db.Column(db.Text)
    request_method = db.Column(db.String(10))  # GET, POST, etc.
    request_path = db.Column(db.String(500))

    # Additional details (flexible JSON storage)
    details = db.Column(db.JSON)

    # Result tracking
    success = db.Column(db.Boolean, default=True)
    error_message = db.Column(db.Text)

    # Relationships
    user = db.relationship('User', backref='audit_logs')
    company = db.relationship('Company', backref='audit_logs')

    def __repr__(self):
        return f'<AuditLog {self.action_type} user={self.user_id} at {self.timestamp}>'

    def to_dict(self):
        """Convert to dictionary for JSON export."""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'user_id': self.user_id,
            'company_id': self.company_id,
            'action_type': self.action_type,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'request_method': self.request_method,
            'request_path': self.request_path,
            'details': self.details,
            'success': self.success,
            'error_message': self.error_message
        }


class WorkspaceSession(db.Model):
    """
    Track workspace usage sessions for billing and compliance.

    Purpose: Monitor workspace access patterns, calculate usage hours,
    provide evidence of service delivery for PayTR disputes.
    """
    __tablename__ = 'workspace_sessions'

    id = db.Column(db.Integer, primary_key=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspaces.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    # Session timing
    started_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    ended_at = db.Column(db.DateTime)
    duration_seconds = db.Column(db.Integer)  # Calculated when session ends

    # Activity tracking
    last_activity_at = db.Column(db.DateTime, default=datetime.utcnow)
    activity_count = db.Column(db.Integer, default=0)  # Number of requests during session

    # Request context
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)

    # Session metadata
    session_id = db.Column(db.String(100), index=True)  # Browser session ID
    access_method = db.Column(db.String(20))  # 'web', 'api', 'ssh'

    # Relationships
    workspace = db.relationship('Workspace', backref='sessions')
    user = db.relationship('User', backref='workspace_sessions')

    def __repr__(self):
        duration = self.get_duration_minutes()
        return f'<WorkspaceSession ws={self.workspace_id} duration={duration}min>'

    def to_dict(self):
        """Convert to dictionary for JSON export."""
        return {
            'id': self.id,
            'workspace_id': self.workspace_id,
            'user_id': self.user_id,
            'started_at': self.started_at.isoformat(),
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'duration_seconds': self.duration_seconds,
            'duration_minutes': self.get_duration_minutes(),
            'last_activity_at': self.last_activity_at.isoformat(),
            'activity_count': self.activity_count,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'session_id': self.session_id,
            'access_method': self.access_method
        }

    def get_duration_minutes(self):
        """Calculate session duration in minutes."""
        if self.duration_seconds:
            return round(self.duration_seconds / 60, 2)
        elif self.ended_at:
            duration = (self.ended_at - self.started_at).total_seconds()
            return round(duration / 60, 2)
        else:
            # Ongoing session
            duration = (datetime.utcnow() - self.started_at).total_seconds()
            return round(duration / 60, 2)

    def end_session(self):
        """End the session and calculate final duration."""
        if not self.ended_at:
            self.ended_at = datetime.utcnow()
            self.duration_seconds = int((self.ended_at - self.started_at).total_seconds())

    def update_activity(self):
        """Update last activity timestamp and increment counter."""
        self.last_activity_at = datetime.utcnow()
        self.activity_count += 1

    def is_active(self, timeout_minutes=30):
        """Check if session is still active (no activity for more than timeout)."""
        if self.ended_at:
            return False
        idle_time = (datetime.utcnow() - self.last_activity_at).total_seconds() / 60
        return idle_time < timeout_minutes


class EmailLog(db.Model):
    """
    Track all email communications for chargeback evidence.
    Purpose: Provide proof of communication for PayTR disputes.
    """
    __tablename__ = 'email_logs'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    # User and company tracking
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), index=True)

    # Email details
    email_type = db.Column(db.String(50), nullable=False, index=True)  # 'registration', 'payment_confirmation', etc.
    recipient_email = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.Text)
    content_hash = db.Column(db.String(64))  # SHA-256 hash for verification

    # Delivery tracking
    sent_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    delivery_status = db.Column(db.String(20), default='sent')  # 'sent', 'delivered', 'bounced', 'failed'
    mailjet_message_id = db.Column(db.String(100))  # External provider tracking
    opened_at = db.Column(db.DateTime)
    clicked_at = db.Column(db.DateTime)

    # Relationships
    user = db.relationship('User', backref='email_logs')
    company = db.relationship('Company', backref='email_logs')

    def __repr__(self):
        return f'<EmailLog {self.id}: {self.email_type} to {self.recipient_email}>'

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'user_id': self.user_id,
            'company_id': self.company_id,
            'email_type': self.email_type,
            'recipient_email': self.recipient_email,
            'subject': self.subject,
            'content_hash': self.content_hash,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'delivery_status': self.delivery_status,
            'mailjet_message_id': self.mailjet_message_id,
            'opened_at': self.opened_at.isoformat() if self.opened_at else None,
            'clicked_at': self.clicked_at.isoformat() if self.clicked_at else None
        }


class WorkspaceTemplate(db.Model):
    """Workspace template model for pre-configured environments."""
    __tablename__ = 'workspace_templates'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))  # web, data-science, mobile, devops, etc.
    visibility = db.Column(db.String(20), nullable=False, default='company')  # official, company, user
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    # Template configuration stored as JSON
    # Schema: {
    #   "base_image": "python:3.11",
    #   "packages": ["jupyter", "pandas", "numpy"],
    #   "extensions": ["ms-python.python", "ms-toolsai.jupyter"],
    #   "repositories": [{"url": "...", "branch": "..."}],
    #   "settings": {...},
    #   "environment": {"KEY": "value"},
    #   "post_create_script": "pip install -r requirements.txt"
    # }
    config = db.Column(db.JSON, nullable=False)

    # Ownership
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Metadata
    usage_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    workspaces = db.relationship('Workspace', backref='template', lazy='dynamic')
    creator = db.relationship('User', foreign_keys=[created_by])
    company = db.relationship('Company', backref=db.backref('templates', lazy='dynamic'))

    def __repr__(self):
        return f'<WorkspaceTemplate {self.name} ({self.category})>'

    def increment_usage(self):
        """Increment usage counter when template is used."""
        self.usage_count += 1
        db.session.commit()

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'visibility': self.visibility,
            'is_active': self.is_active,
            'config': self.config,
            'company_id': self.company_id,
            'created_by': self.created_by,
            'usage_count': self.usage_count,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
