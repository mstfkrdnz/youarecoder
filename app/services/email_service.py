"""
Email service for sending transactional emails via Mailjet.
Handles all email operations including registration, password reset, workspace notifications, and security alerts.
"""
from flask import current_app, render_template
from flask_mail import Message
from app import mail
from threading import Thread
from datetime import datetime


def send_async_email(app, msg):
    """
    Send email asynchronously in a background thread.

    Args:
        app: Flask application instance
        msg: Flask-Mail Message object
    """
    with app.app_context():
        mail.send(msg)


def send_email(subject, recipients, text_body, html_body, sender=None):
    """
    Send email via Mailjet SMTP.

    Args:
        subject: Email subject line
        recipients: List of recipient email addresses
        text_body: Plain text version of email
        html_body: HTML version of email
        sender: Sender email address (default from config)

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    if sender is None:
        sender = current_app.config['MAIL_DEFAULT_SENDER']

    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body

    try:
        # In testing mode, send synchronously
        if current_app.config.get('TESTING'):
            mail.send(msg)
        else:
            # Send asynchronously in production/development (non-blocking)
            Thread(target=send_async_email, args=(current_app._get_current_object(), msg)).start()

        current_app.logger.info(f"Email sent to {recipients}: {subject}")
        return True

    except Exception as e:
        current_app.logger.error(f"Failed to send email to {recipients}: {str(e)}")
        return False


def send_registration_email(user):
    """
    Send welcome email after successful registration.

    Args:
        user: User model instance with email, full_name, company relationship

    Returns:
        bool: True if email sent successfully
    """
    subject = "Welcome to YouAreCoder! 🎉"

    try:
        html_body = render_template('email/registration.html', user=user)
        text_body = render_template('email/registration.txt', user=user)
        return send_email(subject, [user.email], text_body, html_body)

    except Exception as e:
        current_app.logger.error(f"Failed to render registration email for {user.email}: {str(e)}")
        return False


def send_password_reset_email(user, reset_token):
    """
    Send password reset email with secure token link.

    Args:
        user: User model instance
        reset_token: Secure token for password reset (should expire in 1 hour)

    Returns:
        bool: True if email sent successfully
    """
    reset_url = f"https://youarecoder.com/auth/reset-password/{reset_token}"
    subject = "Reset Your Password - YouAreCoder 🔒"

    try:
        html_body = render_template('email/password_reset.html', user=user, reset_url=reset_url)
        text_body = render_template('email/password_reset.txt', user=user, reset_url=reset_url)
        return send_email(subject, [user.email], text_body, html_body)

    except Exception as e:
        current_app.logger.error(f"Failed to render password reset email for {user.email}: {str(e)}")
        return False


def send_workspace_ready_email(user, workspace):
    """
    Send email notification when workspace is provisioned and ready to use.

    Args:
        user: User model instance
        workspace: Workspace model instance with name, subdomain, port, disk_quota_gb, get_url() method

    Returns:
        bool: True if email sent successfully
    """
    subject = f"Your Workspace '{workspace.name}' is Ready! 🚀"

    try:
        html_body = render_template('email/workspace_ready.html', user=user, workspace=workspace)
        text_body = render_template('email/workspace_ready.txt', user=user, workspace=workspace)
        return send_email(subject, [user.email], text_body, html_body)

    except Exception as e:
        current_app.logger.error(f"Failed to render workspace ready email for {user.email}: {str(e)}")
        return False


def send_security_alert_email(user, alert_type, details):
    """
    Send security alert email for suspicious activity or important security events.

    Args:
        user: User model instance
        alert_type: Type of security alert ('failed_login', 'unusual_location', 'password_changed', etc.)
        details: Dictionary with alert details (timestamp, ip_address, location, user_agent, etc.)

    Returns:
        bool: True if email sent successfully

    Example:
        send_security_alert_email(
            user=current_user,
            alert_type='failed_login',
            details={
                'timestamp': '2025-10-27 14:30:00 UTC',
                'ip_address': '192.168.1.1',
                'location': 'Istanbul, Turkey',
                'user_agent': 'Mozilla/5.0...'
            }
        )
    """
    subject = "Security Alert - YouAreCoder 🔒"

    # Ensure timestamp is present
    if 'timestamp' not in details:
        details['timestamp'] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

    try:
        html_body = render_template('email/security_alert.html', user=user, alert_type=alert_type, details=details)
        text_body = render_template('email/security_alert.txt', user=user, alert_type=alert_type, details=details)
        return send_email(subject, [user.email], text_body, html_body)

    except Exception as e:
        current_app.logger.error(f"Failed to render security alert email for {user.email}: {str(e)}")
        return False


def send_payment_success_email(user, payment, invoice, subscription):
    """
    Send payment success confirmation email with invoice details.

    Args:
        user: User model instance (company admin)
        payment: Payment model instance with transaction details
        invoice: Invoice model instance with billing information
        subscription: Subscription model instance with plan details

    Returns:
        bool: True if email sent successfully

    Example:
        send_payment_success_email(
            user=admin_user,
            payment=payment_record,
            invoice=generated_invoice,
            subscription=active_subscription
        )
    """
    subject = "Payment Successful - YouAreCoder"

    try:
        html_body = render_template(
            'email/payment_success.html',
            user=user,
            payment=payment,
            invoice=invoice,
            subscription=subscription
        )
        text_body = render_template(
            'email/payment_success.txt',
            user=user,
            payment=payment,
            invoice=invoice,
            subscription=subscription
        )
        return send_email(subject, [user.email], text_body, html_body)

    except Exception as e:
        current_app.logger.error(f"Failed to render payment success email for {user.email}: {str(e)}")
        return False


def send_payment_failed_email(user, payment):
    """
    Send payment failure alert email with retry instructions.

    Args:
        user: User model instance (company admin)
        payment: Payment model instance with failure details

    Returns:
        bool: True if email sent successfully

    Example:
        send_payment_failed_email(
            user=admin_user,
            payment=failed_payment_record
        )
    """
    subject = "Payment Failed - YouAreCoder"

    try:
        html_body = render_template(
            'email/payment_failed.html',
            user=user,
            payment=payment
        )
        text_body = render_template(
            'email/payment_failed.txt',
            user=user,
            payment=payment
        )
        return send_email(subject, [user.email], text_body, html_body)

    except Exception as e:
        current_app.logger.error(f"Failed to render payment failed email for {user.email}: {str(e)}")
        return False


def send_trial_expiry_reminder_email(user, subscription, days_remaining):
    """
    Send trial period expiration reminder email.

    Args:
        user: User model instance (company admin)
        subscription: Subscription model instance with trial details
        days_remaining: Number of days until trial expires (int)

    Returns:
        bool: True if email sent successfully

    Example:
        send_trial_expiry_reminder_email(
            user=admin_user,
            subscription=trial_subscription,
            days_remaining=7
        )
    """
    subject = f"Your Trial Expires in {days_remaining} Days - YouAreCoder"

    try:
        html_body = render_template(
            'email/trial_expiry_reminder.html',
            user=user,
            subscription=subscription,
            days_remaining=days_remaining
        )
        text_body = render_template(
            'email/trial_expiry_reminder.txt',
            user=user,
            subscription=subscription,
            days_remaining=days_remaining
        )
        return send_email(subject, [user.email], text_body, html_body)

    except Exception as e:
        current_app.logger.error(f"Failed to render trial expiry email for {user.email}: {str(e)}")
        return False
