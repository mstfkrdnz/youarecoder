"""
Audit Logger Service - Central logging for all system activities.

Purpose: PayTR USD/EUR compliance - track all user activities for chargeback disputes.
Features: Automatic logging, decorator support, bulk insert, IP tracking.
"""
from functools import wraps
from flask import request, current_app
from flask_login import current_user
from datetime import datetime
from app import db
from app.models import AuditLog, WorkspaceSession


def get_real_ip():
    """
    Get real client IP address, handling reverse proxy (Traefik).

    Returns:
        str: Client IP address
    """
    # X-Forwarded-For can contain multiple IPs: "client, proxy1, proxy2"
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()

    if request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')

    return request.remote_addr


class AuditLogger:
    """Central audit logging service."""

    @staticmethod
    def log(action_type, resource_type=None, resource_id=None, details=None,
            success=True, error_message=None, user_id=None, company_id=None):
        """
        Log an audit event.

        Args:
            action_type (str): Type of action (e.g., 'login', 'workspace_create', 'payment_success')
            resource_type (str, optional): Type of resource affected
            resource_id (int, optional): ID of the affected resource
            details (dict, optional): Additional details as JSON
            success (bool): Whether the action was successful
            error_message (str, optional): Error message if action failed
            user_id (int, optional): User ID (defaults to current_user)
            company_id (int, optional): Company ID (defaults to current_user.company_id)

        Returns:
            AuditLog: The created audit log entry
        """
        try:
            # Get user and company from current context if not provided
            if user_id is None and current_user and current_user.is_authenticated:
                user_id = current_user.id

            if company_id is None and current_user and current_user.is_authenticated:
                company_id = current_user.company_id

            # Create audit log entry
            log_entry = AuditLog(
                timestamp=datetime.utcnow(),
                user_id=user_id,
                company_id=company_id,
                action_type=action_type,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=get_real_ip(),
                user_agent=request.headers.get('User-Agent', '')[:1000] if request else None,
                request_method=request.method if request else None,
                request_path=request.path if request else None,
                details=details,
                success=success,
                error_message=error_message
            )

            db.session.add(log_entry)
            db.session.commit()

            return log_entry

        except Exception as e:
            # Don't let audit logging break the main flow
            current_app.logger.error(f"Audit logging failed: {str(e)}")
            db.session.rollback()
            return None

    @staticmethod
    def log_login(user, success=True, failure_reason=None):
        """Log user login attempt."""
        return AuditLogger.log(
            action_type='login',
            resource_type='user',
            resource_id=user.id if user else None,
            details={'email': user.email if user else None},
            success=success,
            error_message=failure_reason,
            user_id=user.id if user else None,
            company_id=user.company_id if user else None
        )

    @staticmethod
    def log_logout(user):
        """Log user logout."""
        return AuditLogger.log(
            action_type='logout',
            resource_type='user',
            resource_id=user.id,
            user_id=user.id,
            company_id=user.company_id
        )

    @staticmethod
    def log_workspace_create(workspace):
        """Log workspace creation."""
        return AuditLogger.log(
            action_type='workspace_create',
            resource_type='workspace',
            resource_id=workspace.id,
            details={
                'workspace_name': workspace.name,
                'linux_user': workspace.linux_user,
                'subdomain': workspace.subdomain
            }
        )

    @staticmethod
    def log_workspace_delete(workspace):
        """Log workspace deletion."""
        return AuditLogger.log(
            action_type='workspace_delete',
            resource_type='workspace',
            resource_id=workspace.id,
            details={
                'workspace_name': workspace.name,
                'linux_user': workspace.linux_user
            }
        )

    @staticmethod
    def log_workspace_access(workspace, session_id=None):
        """Log workspace access."""
        return AuditLogger.log(
            action_type='workspace_access',
            resource_type='workspace',
            resource_id=workspace.id,
            details={
                'workspace_name': workspace.name,
                'subdomain': workspace.subdomain,
                'session_id': session_id
            }
        )

    @staticmethod
    def log_payment(payment, action='payment_success'):
        """Log payment event."""
        return AuditLogger.log(
            action_type=action,
            resource_type='payment',
            resource_id=payment.id,
            details={
                'amount': payment.amount,
                'currency': payment.currency,
                'payment_method': payment.payment_method,
                'merchant_oid': payment.merchant_oid,
                'paytr_transaction_id': payment.paytr_transaction_id
            },
            company_id=payment.company_id
        )

    @staticmethod
    def log_subscription_change(subscription, action='subscription_update'):
        """Log subscription change."""
        return AuditLogger.log(
            action_type=action,
            resource_type='subscription',
            resource_id=subscription.id,
            details={
                'plan': subscription.plan,
                'status': subscription.status,
                'trial_end': subscription.trial_end.isoformat() if subscription.trial_end else None,
                'current_period_start': subscription.current_period_start.isoformat() if subscription.current_period_start else None,
                'current_period_end': subscription.current_period_end.isoformat() if subscription.current_period_end else None
            },
            company_id=subscription.company_id
        )


class WorkspaceSessionTracker:
    """Track workspace usage sessions."""

    @staticmethod
    def start_session(workspace, user, session_id=None, access_method='web'):
        """
        Start a new workspace session.

        Args:
            workspace: Workspace object
            user: User object
            session_id: Browser/API session ID
            access_method: 'web', 'api', or 'ssh'

        Returns:
            WorkspaceSession: Created session object
        """
        try:
            session = WorkspaceSession(
                workspace_id=workspace.id,
                user_id=user.id,
                started_at=datetime.utcnow(),
                last_activity_at=datetime.utcnow(),
                ip_address=get_real_ip(),
                user_agent=request.headers.get('User-Agent', '')[:1000] if request else None,
                session_id=session_id,
                access_method=access_method,
                activity_count=1
            )

            db.session.add(session)
            db.session.commit()

            # Also log in audit trail
            AuditLogger.log_workspace_access(workspace, session_id=session_id)

            return session

        except Exception as e:
            current_app.logger.error(f"Session tracking failed: {str(e)}")
            db.session.rollback()
            return None

    @staticmethod
    def end_session(session):
        """End a workspace session."""
        try:
            if session and not session.ended_at:
                session.end_session()
                db.session.commit()
                return True
        except Exception as e:
            current_app.logger.error(f"Session end failed: {str(e)}")
            db.session.rollback()
        return False

    @staticmethod
    def update_activity(session):
        """Update session activity."""
        try:
            if session and session.is_active():
                session.update_activity()
                db.session.commit()
                return True
        except Exception as e:
            current_app.logger.error(f"Session activity update failed: {str(e)}")
            db.session.rollback()
        return False

    @staticmethod
    def get_active_session(workspace_id, user_id, session_id=None):
        """
        Get active session for workspace and user.

        Args:
            workspace_id: Workspace ID
            user_id: User ID
            session_id: Optional browser session ID

        Returns:
            WorkspaceSession or None
        """
        query = WorkspaceSession.query.filter_by(
            workspace_id=workspace_id,
            user_id=user_id,
            ended_at=None
        )

        if session_id:
            query = query.filter_by(session_id=session_id)

        # Get most recent active session
        session = query.order_by(WorkspaceSession.started_at.desc()).first()

        # Check if it's still active (not idle for more than 30 minutes)
        if session and not session.is_active(timeout_minutes=30):
            # Auto-end idle session
            WorkspaceSessionTracker.end_session(session)
            return None

        return session

    @staticmethod
    def get_workspace_usage_stats(workspace_id, start_date=None, end_date=None):
        """
        Get usage statistics for a workspace.

        Args:
            workspace_id: Workspace ID
            start_date: Start date filter (optional)
            end_date: End date filter (optional)

        Returns:
            dict: Usage statistics
        """
        query = WorkspaceSession.query.filter_by(workspace_id=workspace_id)

        if start_date:
            query = query.filter(WorkspaceSession.started_at >= start_date)
        if end_date:
            query = query.filter(WorkspaceSession.started_at <= end_date)

        sessions = query.all()

        total_sessions = len(sessions)
        total_seconds = sum(s.duration_seconds or 0 for s in sessions if s.ended_at)
        total_hours = round(total_seconds / 3600, 2) if total_seconds else 0

        return {
            'total_sessions': total_sessions,
            'total_hours': total_hours,
            'total_minutes': round(total_seconds / 60, 2) if total_seconds else 0,
            'average_session_minutes': round((total_seconds / total_sessions) / 60, 2) if total_sessions > 0 else 0
        }


def audit_action(action_type, resource_type=None):
    """
    Decorator for automatic audit logging.

    Usage:
        @audit_action('workspace_create', 'workspace')
        def create_workspace():
            ...

    Args:
        action_type: Type of action to log
        resource_type: Type of resource (optional)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Execute the function
            result = f(*args, **kwargs)

            # Log the action
            try:
                AuditLogger.log(
                    action_type=action_type,
                    resource_type=resource_type,
                    success=True
                )
            except Exception as e:
                current_app.logger.error(f"Audit decorator logging failed: {str(e)}")

            return result

        return decorated_function
    return decorator
