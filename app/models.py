"""
Database models for YouAreCoder platform.
"""
from datetime import datetime
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
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    users = db.relationship('User', backref='company', lazy='dynamic', cascade='all, delete-orphan')
    workspaces = db.relationship('Workspace', backref='company', lazy='dynamic', cascade='all, delete-orphan')

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


class User(UserMixin, db.Model):
    """User model with Flask-Login integration."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
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

    # Relationships
    workspaces = db.relationship('Workspace', backref='owner', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.username} ({self.email})>'

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
            'username': self.username,
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
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

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
