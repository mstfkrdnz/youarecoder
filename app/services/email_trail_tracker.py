"""
Email Trail Tracker Service

Track all email communications for PayTR chargeback evidence.
Provides comprehensive email history with delivery tracking.
"""
import hashlib
import logging
from datetime import datetime
from flask import current_app
from flask_login import current_user

from app import db
from app.models import EmailLog

logger = logging.getLogger(__name__)


class EmailTrailTracker:
    """Track email communications for dispute evidence."""

    @staticmethod
    def log_email(email_type, recipient_email, subject, content=None,
                  user_id=None, company_id=None, mailjet_message_id=None):
        """
        Log an email that was sent.

        Args:
            email_type: Type of email (registration, payment_confirmation, etc.)
            recipient_email: Email address of recipient
            subject: Email subject line
            content: Email body content (optional, for hash generation)
            user_id: User ID (auto-detected if not provided)
            company_id: Company ID (auto-detected if not provided)
            mailjet_message_id: External tracking ID from Mailjet

        Returns:
            EmailLog entry or None if logging failed
        """
        try:
            # Auto-detect user/company from current context
            if user_id is None and current_user and current_user.is_authenticated:
                user_id = current_user.id
            if company_id is None and current_user and current_user.is_authenticated:
                company_id = current_user.company_id

            # Generate content hash for verification
            content_hash = None
            if content:
                content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()

            email_log = EmailLog(
                timestamp=datetime.utcnow(),
                user_id=user_id,
                company_id=company_id,
                email_type=email_type,
                recipient_email=recipient_email,
                subject=subject,
                content_hash=content_hash,
                sent_at=datetime.utcnow(),
                delivery_status='sent',
                mailjet_message_id=mailjet_message_id
            )

            db.session.add(email_log)
            db.session.commit()

            logger.info(f"Email logged: {email_type} to {recipient_email} (ID: {email_log.id})")
            return email_log

        except Exception as e:
            logger.error(f"Email logging failed: {str(e)}")
            db.session.rollback()
            return None

    @staticmethod
    def log_registration_email(user, mailjet_message_id=None):
        """Log registration confirmation email."""
        return EmailTrailTracker.log_email(
            email_type='registration',
            recipient_email=user.email,
            subject='Welcome to YouAreCoder',
            user_id=user.id,
            company_id=user.company_id,
            mailjet_message_id=mailjet_message_id
        )

    @staticmethod
    def log_payment_confirmation(user, payment, mailjet_message_id=None):
        """Log payment confirmation email."""
        return EmailTrailTracker.log_email(
            email_type='payment_confirmation',
            recipient_email=user.email,
            subject=f'Payment Confirmed - Order {payment.merchant_oid}',
            user_id=user.id,
            company_id=user.company_id,
            mailjet_message_id=mailjet_message_id
        )

    @staticmethod
    def log_workspace_created(user, workspace, mailjet_message_id=None):
        """Log workspace creation notification email."""
        return EmailTrailTracker.log_email(
            email_type='workspace_created',
            recipient_email=user.email,
            subject=f'Workspace Created: {workspace.dev_name}',
            user_id=user.id,
            company_id=user.company_id,
            mailjet_message_id=mailjet_message_id
        )

    @staticmethod
    def log_subscription_change(user, action, plan, mailjet_message_id=None):
        """Log subscription change notification email."""
        return EmailTrailTracker.log_email(
            email_type='subscription_change',
            recipient_email=user.email,
            subject=f'Subscription {action.title()}: {plan}',
            user_id=user.id,
            company_id=user.company_id,
            mailjet_message_id=mailjet_message_id
        )

    @staticmethod
    def log_password_reset(email, mailjet_message_id=None):
        """Log password reset email."""
        return EmailTrailTracker.log_email(
            email_type='password_reset',
            recipient_email=email,
            subject='Password Reset Request',
            mailjet_message_id=mailjet_message_id
        )

    @staticmethod
    def get_email_history(user_id=None, company_id=None, email_type=None,
                          start_date=None, end_date=None, limit=100):
        """
        Get email history for a user or company.

        Args:
            user_id: Filter by user ID
            company_id: Filter by company ID
            email_type: Filter by email type
            start_date: Filter emails after this date
            end_date: Filter emails before this date
            limit: Maximum number of results

        Returns:
            List of EmailLog entries
        """
        try:
            query = EmailLog.query

            if user_id:
                query = query.filter_by(user_id=user_id)
            if company_id:
                query = query.filter_by(company_id=company_id)
            if email_type:
                query = query.filter_by(email_type=email_type)
            if start_date:
                query = query.filter(EmailLog.sent_at >= start_date)
            if end_date:
                query = query.filter(EmailLog.sent_at <= end_date)

            query = query.order_by(EmailLog.sent_at.desc()).limit(limit)

            return query.all()

        except Exception as e:
            logger.error(f"Error retrieving email history: {str(e)}")
            return []

    @staticmethod
    def update_delivery_status(email_log_id, status, opened_at=None, clicked_at=None):
        """
        Update email delivery status (for webhook integration).

        Args:
            email_log_id: EmailLog ID
            status: New status (delivered, bounced, failed)
            opened_at: Timestamp when email was opened
            clicked_at: Timestamp when link was clicked

        Returns:
            Updated EmailLog or None
        """
        try:
            email_log = EmailLog.query.get(email_log_id)
            if not email_log:
                logger.warning(f"EmailLog {email_log_id} not found")
                return None

            email_log.delivery_status = status
            if opened_at:
                email_log.opened_at = opened_at
            if clicked_at:
                email_log.clicked_at = clicked_at

            db.session.commit()

            logger.info(f"Email {email_log_id} delivery status updated: {status}")
            return email_log

        except Exception as e:
            logger.error(f"Error updating delivery status: {str(e)}")
            db.session.rollback()
            return None

    @staticmethod
    def verify_email_sent(email_log_id):
        """
        Verify that an email was successfully sent.

        Args:
            email_log_id: EmailLog ID

        Returns:
            Boolean indicating if email was sent
        """
        try:
            email_log = EmailLog.query.get(email_log_id)
            if not email_log:
                return False

            return email_log.delivery_status in ['sent', 'delivered']

        except Exception as e:
            logger.error(f"Error verifying email: {str(e)}")
            return False
