"""
Tests for payment email notifications.
Comprehensive testing of email sending for payment success, failure, and trial expiry.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from app.models import User, Company, Subscription, Payment, Invoice
from app.services.email_service import (
    send_payment_success_email,
    send_payment_failed_email,
    send_trial_expiry_reminder_email
)
from app import db


@pytest.fixture
def company_with_subscription(db_session):
    """Create company with active subscription for testing."""
    company = Company(
        name='Test Company',
        subdomain='testco',
        plan='team',
        status='active',
        max_workspaces=20
    )
    db_session.add(company)
    db_session.flush()

    subscription = Subscription(
        company_id=company.id,
        plan='team',
        status='active',
        trial_starts_at=datetime.utcnow() - timedelta(days=14),
        trial_ends_at=datetime.utcnow() + timedelta(days=14),
        current_period_start=datetime.utcnow(),
        current_period_end=datetime.utcnow() + timedelta(days=30)
    )
    db_session.add(subscription)
    db_session.flush()

    user = User(
        email='admin@testco.com',
        full_name='Test Admin',
        password_hash='hashed_password',
        company_id=company.id,
        role='admin',
        email_verified=True
    )
    db_session.add(user)
    db_session.commit()

    # Attach objects to fixture for access
    company.subscription_obj = subscription
    company.admin_user = user

    return company


@pytest.fixture
def successful_payment(db_session, company_with_subscription):
    """Create successful payment record for testing."""
    payment = Payment(
        company_id=company_with_subscription.id,
        subscription_id=company_with_subscription.subscription_obj.id,
        paytr_merchant_oid='YAC-1234567890-1',
        amount=9900,  # $99.00 in cents
        currency='USD',
        status='success',
        payment_type='initial',
        test_mode=True
    )
    db_session.add(payment)
    db_session.flush()

    invoice = Invoice(
        company_id=company_with_subscription.id,
        payment_id=payment.id,
        invoice_number='INV-2025-0001',
        subtotal=9900,
        tax_amount=0,
        total_amount=9900,
        currency='USD',
        period_start=datetime.utcnow(),
        period_end=datetime.utcnow() + timedelta(days=30),
        invoice_date=datetime.utcnow(),
        due_date=datetime.utcnow(),
        paid_at=datetime.utcnow(),
        status='paid'
    )
    db_session.add(invoice)
    db_session.commit()

    payment.invoice_obj = invoice
    return payment


@pytest.fixture
def failed_payment(db_session, company_with_subscription):
    """Create failed payment record for testing."""
    payment = Payment(
        company_id=company_with_subscription.id,
        subscription_id=company_with_subscription.subscription_obj.id,
        paytr_merchant_oid='YAC-9876543210-1',
        amount=9900,
        currency='USD',
        status='failed',
        payment_type='initial',
        test_mode=True,
        failure_reason_code='insufficient_funds',
        failure_reason_message='Insufficient funds in account'
    )
    db_session.add(payment)
    db_session.commit()

    return payment


class TestPaymentSuccessEmail:
    """Test payment success email functionality."""

    def test_send_payment_success_email(self, company_with_subscription, successful_payment):
        """Test successful payment email is sent correctly."""
            user = company_with_subscription.admin_user
            payment = successful_payment
            invoice = payment.invoice_obj
            subscription = company_with_subscription.subscription_obj

            with patch('app.services.email_service.mail.send') as mock_send:
                result = send_payment_success_email(user, payment, invoice, subscription)

                assert result is True
                assert mock_send.called
                assert mock_send.call_count == 1

    def test_payment_success_email_content(self, company_with_subscription, successful_payment):
        """Test payment success email contains correct content."""
            user = company_with_subscription.admin_user
            payment = successful_payment
            invoice = payment.invoice_obj
            subscription = company_with_subscription.subscription_obj

            with patch('app.services.email_service.mail.send') as mock_send:
                send_payment_success_email(user, payment, invoice, subscription)

                # Get the message object from the mock call
                call_args = mock_send.call_args
                msg = call_args[0][0]

                assert msg.subject == "Payment Successful - YouAreCoder"
                assert user.email in msg.recipients
                assert invoice.invoice_number in msg.html
                assert f"{payment.amount / 100.0:.2f}" in msg.html  # Amount formatted
                assert subscription.plan in msg.html

    def test_payment_success_email_template_rendering(self, company_with_subscription, successful_payment):
        """Test payment success email template renders without errors."""
            user = company_with_subscription.admin_user
            payment = successful_payment
            invoice = payment.invoice_obj
            subscription = company_with_subscription.subscription_obj

            # Test HTML template rendering
            from flask import render_template
            html_body = render_template(
                'email/payment_success.html',
                user=user,
                payment=payment,
                invoice=invoice,
                subscription=subscription
            )
            assert html_body is not None
            assert len(html_body) > 0
            assert 'Payment Successful' in html_body

            # Test text template rendering
            text_body = render_template(
                'email/payment_success.txt',
                user=user,
                payment=payment,
                invoice=invoice,
                subscription=subscription
            )
            assert text_body is not None
            assert len(text_body) > 0

    def test_payment_success_email_handles_errors(self, company_with_subscription, successful_payment):
        """Test payment success email handles template errors gracefully."""
            user = company_with_subscription.admin_user
            payment = successful_payment
            invoice = payment.invoice_obj
            subscription = company_with_subscription.subscription_obj

            with patch('app.services.email_service.render_template', side_effect=Exception("Template error")):
                result = send_payment_success_email(user, payment, invoice, subscription)
                assert result is False


class TestPaymentFailedEmail:
    """Test payment failure email functionality."""

    def test_send_payment_failed_email(self, company_with_subscription, failed_payment):
        """Test failed payment email is sent correctly."""
            user = company_with_subscription.admin_user
            payment = failed_payment

            with patch('app.services.email_service.mail.send') as mock_send:
                result = send_payment_failed_email(user, payment)

                assert result is True
                assert mock_send.called
                assert mock_send.call_count == 1

    def test_payment_failed_email_content(self, company_with_subscription, failed_payment):
        """Test payment failure email contains correct content."""
            user = company_with_subscription.admin_user
            payment = failed_payment

            with patch('app.services.email_service.mail.send') as mock_send:
                send_payment_failed_email(user, payment)

                call_args = mock_send.call_args
                msg = call_args[0][0]

                assert msg.subject == "Payment Failed - YouAreCoder"
                assert user.email in msg.recipients
                assert payment.failure_reason_message in msg.html
                assert f"{payment.amount / 100.0:.2f}" in msg.html

    def test_payment_failed_email_template_rendering(self, company_with_subscription, failed_payment):
        """Test payment failure email template renders without errors."""
            user = company_with_subscription.admin_user
            payment = failed_payment

            from flask import render_template
            html_body = render_template(
                'email/payment_failed.html',
                user=user,
                payment=payment
            )
            assert html_body is not None
            assert 'Payment Failed' in html_body
            assert payment.failure_reason_message in html_body

            text_body = render_template(
                'email/payment_failed.txt',
                user=user,
                payment=payment
            )
            assert text_body is not None

    def test_payment_failed_email_handles_errors(self, company_with_subscription, failed_payment):
        """Test payment failure email handles errors gracefully."""
            user = company_with_subscription.admin_user
            payment = failed_payment

            with patch('app.services.email_service.render_template', side_effect=Exception("Template error")):
                result = send_payment_failed_email(user, payment)
                assert result is False


class TestTrialExpiryReminderEmail:
    """Test trial expiry reminder email functionality."""

    def test_send_trial_expiry_reminder_email(self, company_with_subscription):
        """Test trial expiry reminder email is sent correctly."""
            user = company_with_subscription.admin_user
            subscription = company_with_subscription.subscription_obj
            days_remaining = 7

            with patch('app.services.email_service.mail.send') as mock_send:
                result = send_trial_expiry_reminder_email(user, subscription, days_remaining)

                assert result is True
                assert mock_send.called
                assert mock_send.call_count == 1

    def test_trial_expiry_email_content(self, company_with_subscription):
        """Test trial expiry email contains correct content."""
            user = company_with_subscription.admin_user
            subscription = company_with_subscription.subscription_obj
            days_remaining = 7

            with patch('app.services.email_service.mail.send') as mock_send:
                send_trial_expiry_reminder_email(user, subscription, days_remaining)

                call_args = mock_send.call_args
                msg = call_args[0][0]

                assert f"Your Trial Expires in {days_remaining} Days" in msg.subject
                assert user.email in msg.recipients
                assert str(days_remaining) in msg.html
                assert subscription.plan in msg.html

    def test_trial_expiry_email_different_days(self, company_with_subscription):
        """Test trial expiry email with different day counts."""
            user = company_with_subscription.admin_user
            subscription = company_with_subscription.subscription_obj

            for days in [1, 3, 7, 14]:
                with patch('app.services.email_service.mail.send') as mock_send:
                    send_trial_expiry_reminder_email(user, subscription, days)

                    call_args = mock_send.call_args
                    msg = call_args[0][0]

                    expected_subject = f"Your Trial Expires in {days} Day{'s' if days != 1 else ''} - YouAreCoder"
                    assert expected_subject in msg.subject

    def test_trial_expiry_email_template_rendering(self, company_with_subscription):
        """Test trial expiry email template renders without errors."""
            user = company_with_subscription.admin_user
            subscription = company_with_subscription.subscription_obj
            days_remaining = 7

            from flask import render_template
            html_body = render_template(
                'email/trial_expiry_reminder.html',
                user=user,
                subscription=subscription,
                days_remaining=days_remaining
            )
            assert html_body is not None
            assert 'Trial is Ending Soon' in html_body
            assert str(days_remaining) in html_body

            text_body = render_template(
                'email/trial_expiry_reminder.txt',
                user=user,
                subscription=subscription,
                days_remaining=days_remaining
            )
            assert text_body is not None

    def test_trial_expiry_email_handles_errors(self, company_with_subscription):
        """Test trial expiry email handles errors gracefully."""
            user = company_with_subscription.admin_user
            subscription = company_with_subscription.subscription_obj
            days_remaining = 7

            with patch('app.services.email_service.render_template', side_effect=Exception("Template error")):
                result = send_trial_expiry_reminder_email(user, subscription, days_remaining)
                assert result is False


class TestPaymentEmailIntegration:
    """Test integration of payment emails with PayTR service."""

    def test_payment_callback_sends_success_email(self, company_with_subscription):
        """Test payment callback triggers success email."""
            from app.services.paytr_service import PayTRService

            # Create a pending payment
            payment = Payment(
                company_id=company_with_subscription.id,
                subscription_id=company_with_subscription.subscription_obj.id,
                paytr_merchant_oid='YAC-TEST-123',
                amount=9900,
                currency='USD',
                status='pending',
                payment_type='initial',
                test_mode=True
            )
            db.session.add(payment)
            db.session.commit()

            # Mock PayTR callback data
            import base64
            import hmac
            import hashlib
            from config import Config

            merchant_oid = 'YAC-TEST-123'
            status = 'success'
            total_amount = '9900'

            # Generate valid hash
            hash_str = f"{merchant_oid}{Config.PAYTR_MERCHANT_SALT}{status}{total_amount}"
            valid_hash = base64.b64encode(
                hmac.new(
                    Config.PAYTR_MERCHANT_KEY.encode('utf-8'),
                    hash_str.encode('utf-8'),
                    hashlib.sha256
                ).digest()
            ).decode('utf-8')

            post_data = {
                'merchant_oid': merchant_oid,
                'status': status,
                'total_amount': total_amount,
                'hash': valid_hash,
                'failed_reason_code': '',
                'failed_reason_msg': ''
            }

            paytr_service = PayTRService()

            with patch('app.services.email_service.mail.send') as mock_send:
                success, message = paytr_service.process_payment_callback(post_data)

                assert success is True
                # Email should be sent after successful payment
                assert mock_send.called

            # Cleanup
            db.session.delete(payment)
            db.session.commit()

    def test_payment_callback_sends_failure_email(self, company_with_subscription):
        """Test payment callback triggers failure email."""
            from app.services.paytr_service import PayTRService

            # Create a pending payment
            payment = Payment(
                company_id=company_with_subscription.id,
                subscription_id=company_with_subscription.subscription_obj.id,
                paytr_merchant_oid='YAC-TEST-456',
                amount=9900,
                currency='USD',
                status='pending',
                payment_type='initial',
                test_mode=True
            )
            db.session.add(payment)
            db.session.commit()

            # Mock PayTR callback data for failure
            import base64
            import hmac
            import hashlib
            from config import Config

            merchant_oid = 'YAC-TEST-456'
            status = 'failed'
            total_amount = '9900'

            # Generate valid hash
            hash_str = f"{merchant_oid}{Config.PAYTR_MERCHANT_SALT}{status}{total_amount}"
            valid_hash = base64.b64encode(
                hmac.new(
                    Config.PAYTR_MERCHANT_KEY.encode('utf-8'),
                    hash_str.encode('utf-8'),
                    hashlib.sha256
                ).digest()
            ).decode('utf-8')

            post_data = {
                'merchant_oid': merchant_oid,
                'status': status,
                'total_amount': total_amount,
                'hash': valid_hash,
                'failed_reason_code': 'insufficient_funds',
                'failed_reason_msg': 'Insufficient funds'
            }

            paytr_service = PayTRService()

            with patch('app.services.email_service.mail.send') as mock_send:
                success, message = paytr_service.process_payment_callback(post_data)

                assert success is True
                # Email should be sent after failed payment
                assert mock_send.called

            # Cleanup
            db.session.delete(payment)
            db.session.commit()
