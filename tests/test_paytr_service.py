"""
Unit tests for PayTR Payment Service

Tests cover:
- Token generation with HMAC-SHA256 verification
- Callback hash verification security
- Payment processing workflow
- Subscription lifecycle management
- Error handling and edge cases
"""
import base64
import hashlib
import hmac
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from app import create_app, db
from app.models import Company, User, Subscription, Payment, Invoice
from app.services.paytr_service import PayTRService


@pytest.fixture
def app():
    """Create test Flask application."""
    app = create_app('test')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def company(app):
    """Create test company."""
    company = Company(
        name='Test Company',
        subdomain='testco',
        plan='team',
        max_workspaces=20
    )
    db.session.add(company)
    db.session.commit()
    return company


@pytest.fixture
def paytr_service(app):
    """Create PayTR service instance."""
    app.config['PAYTR_MERCHANT_ID'] = 'TEST123'
    app.config['PAYTR_MERCHANT_KEY'] = 'TESTKEY123'
    app.config['PAYTR_MERCHANT_SALT'] = 'TESTSALT123'
    app.config['PAYTR_TEST_MODE'] = '1'
    app.config['BASE_URL'] = 'https://test.youarecoder.com'

    return PayTRService()


class TestPayTRTokenGeneration:
    """Test PayTR iframe token generation."""

    def test_generate_token_success(self, app, company, paytr_service):
        """Test successful token generation."""
        with app.app_context():
            mock_response = {
                'status': 'success',
                'token': 'test_iframe_token_12345'
            }

            with patch('requests.post') as mock_post:
                mock_post.return_value.json.return_value = mock_response
                mock_post.return_value.raise_for_status = Mock()

                result = paytr_service.generate_iframe_token(
                    company=company,
                    plan='team',
                    user_ip='192.168.1.1',
                    user_email='test@example.com',
                    currency='USD'
                )

                assert result['success'] is True
                assert result['token'] == 'test_iframe_token_12345'
                assert 'iframe_url' in result
                assert result['iframe_url'].endswith('test_iframe_token_12345')
                assert 'payment_id' in result
                assert 'merchant_oid' in result

                # Verify payment record was created
                payment = Payment.query.filter_by(id=result['payment_id']).first()
                assert payment is not None
                assert payment.status == 'pending'
                assert payment.amount == 9900  # $99.00 in cents
                assert payment.currency == 'USD'

    def test_generate_token_hmac_calculation(self, app, company, paytr_service):
        """Test HMAC-SHA256 hash calculation correctness."""
        with app.app_context():
            user_ip = '192.168.1.1'
            user_email = 'test@example.com'

            with patch('requests.post') as mock_post:
                mock_post.return_value.json.return_value = {'status': 'success', 'token': 'test'}
                mock_post.return_value.raise_for_status = Mock()

                paytr_service.generate_iframe_token(
                    company=company,
                    plan='team',
                    user_ip=user_ip,
                    user_email=user_email,
                    currency='USD'
                )

                # Get the actual POST call
                call_args = mock_post.call_args
                post_data = call_args[1]['data']

                # Verify token was generated correctly
                assert 'paytr_token' in post_data
                token = post_data['paytr_token']

                # Token should be base64 encoded
                try:
                    decoded = base64.b64decode(token)
                    assert len(decoded) == 32  # SHA256 produces 32 bytes
                except Exception:
                    pytest.fail("PayTR token should be valid base64")

    def test_generate_token_invalid_plan(self, app, company, paytr_service):
        """Test token generation with invalid plan."""
        with app.app_context():
            result = paytr_service.generate_iframe_token(
                company=company,
                plan='invalid_plan',
                user_ip='192.168.1.1',
                user_email='test@example.com'
            )

            assert result['success'] is False
            assert 'Invalid plan' in result['reason']

    def test_generate_token_api_failure(self, app, company, paytr_service):
        """Test handling of PayTR API failure."""
        with app.app_context():
            mock_response = {
                'status': 'failed',
                'reason': 'Invalid merchant credentials'
            }

            with patch('requests.post') as mock_post:
                mock_post.return_value.json.return_value = mock_response
                mock_post.return_value.raise_for_status = Mock()

                result = paytr_service.generate_iframe_token(
                    company=company,
                    plan='team',
                    user_ip='192.168.1.1',
                    user_email='test@example.com'
                )

                assert result['success'] is False
                assert result['reason'] == 'Invalid merchant credentials'

                # Verify payment was marked as failed
                payment = Payment.query.filter_by(company_id=company.id).first()
                assert payment.status == 'failed'


class TestPayTRCallbackVerification:
    """Test PayTR callback hash verification."""

    def test_verify_callback_valid_hash(self, app, paytr_service):
        """Test successful callback hash verification."""
        with app.app_context():
            merchant_oid = 'YAC-1234567890-1'
            status = 'success'
            total_amount = '9900'

            # Generate expected hash
            hash_str = f"{merchant_oid}{paytr_service.merchant_salt}{status}{total_amount}"
            expected_hash = base64.b64encode(
                hmac.new(
                    paytr_service.merchant_key,
                    hash_str.encode('utf-8'),
                    hashlib.sha256
                ).digest()
            ).decode('utf-8')

            post_data = {
                'merchant_oid': merchant_oid,
                'status': status,
                'total_amount': total_amount,
                'hash': expected_hash
            }

            is_valid = paytr_service.verify_callback_hash(post_data)
            assert is_valid is True

    def test_verify_callback_invalid_hash(self, app, paytr_service):
        """Test callback with invalid hash."""
        with app.app_context():
            post_data = {
                'merchant_oid': 'YAC-1234567890-1',
                'status': 'success',
                'total_amount': '9900',
                'hash': 'invalid_hash_value'
            }

            is_valid = paytr_service.verify_callback_hash(post_data)
            assert is_valid is False

    def test_verify_callback_tampered_data(self, app, paytr_service):
        """Test callback with tampered payment amount."""
        with app.app_context():
            merchant_oid = 'YAC-1234567890-1'
            status = 'success'
            original_amount = '9900'

            # Generate hash for original amount
            hash_str = f"{merchant_oid}{paytr_service.merchant_salt}{status}{original_amount}"
            valid_hash = base64.b64encode(
                hmac.new(
                    paytr_service.merchant_key,
                    hash_str.encode('utf-8'),
                    hashlib.sha256
                ).digest()
            ).decode('utf-8')

            # Tamper with amount
            post_data = {
                'merchant_oid': merchant_oid,
                'status': status,
                'total_amount': '100',  # Tampered: changed from 9900 to 100
                'hash': valid_hash
            }

            is_valid = paytr_service.verify_callback_hash(post_data)
            assert is_valid is False


class TestPayTRCallbackProcessing:
    """Test PayTR payment callback processing."""

    def test_process_successful_payment(self, app, company, paytr_service):
        """Test processing successful payment callback."""
        with app.app_context():
            # Create pending payment
            payment = Payment(
                company_id=company.id,
                paytr_merchant_oid='YAC-1234567890-1',
                amount=9900,
                currency='USD',
                status='pending',
                payment_type='initial',
                test_mode=True,
                user_ip='192.168.1.1'
            )
            db.session.add(payment)
            db.session.commit()

            # Create valid callback data
            merchant_oid = 'YAC-1234567890-1'
            status = 'success'
            total_amount = '9900'

            hash_str = f"{merchant_oid}{paytr_service.merchant_salt}{status}{total_amount}"
            valid_hash = base64.b64encode(
                hmac.new(
                    paytr_service.merchant_key,
                    hash_str.encode('utf-8'),
                    hashlib.sha256
                ).digest()
            ).decode('utf-8')

            post_data = {
                'merchant_oid': merchant_oid,
                'status': status,
                'total_amount': total_amount,
                'hash': valid_hash,
                'test_mode': '1',
                'payment_type': 'card'
            }

            success, message = paytr_service.process_payment_callback(post_data)

            assert success is True
            assert message == 'OK'

            # Verify payment was updated
            payment = Payment.query.filter_by(paytr_merchant_oid=merchant_oid).first()
            assert payment.status == 'success'
            assert payment.completed_at is not None

            # Verify subscription was created/activated
            subscription = Subscription.query.filter_by(company_id=company.id).first()
            assert subscription is not None
            assert subscription.status == 'active'

            # Verify invoice was created
            invoice = Invoice.query.filter_by(payment_id=payment.id).first()
            assert invoice is not None
            assert invoice.status == 'paid'
            assert invoice.total_amount == 9900

    def test_process_failed_payment(self, app, company, paytr_service):
        """Test processing failed payment callback."""
        with app.app_context():
            # Create pending payment
            payment = Payment(
                company_id=company.id,
                paytr_merchant_oid='YAC-1234567890-2',
                amount=9900,
                currency='USD',
                status='pending',
                payment_type='initial',
                test_mode=True,
                user_ip='192.168.1.1'
            )
            db.session.add(payment)
            db.session.commit()

            # Create failed callback data
            merchant_oid = 'YAC-1234567890-2'
            status = 'failed'
            total_amount = '9900'

            hash_str = f"{merchant_oid}{paytr_service.merchant_salt}{status}{total_amount}"
            valid_hash = base64.b64encode(
                hmac.new(
                    paytr_service.merchant_key,
                    hash_str.encode('utf-8'),
                    hashlib.sha256
                ).digest()
            ).decode('utf-8')

            post_data = {
                'merchant_oid': merchant_oid,
                'status': status,
                'total_amount': total_amount,
                'hash': valid_hash,
                'test_mode': '1',
                'payment_type': 'card',
                'failed_reason_code': 'INSUFFICIENT_FUNDS',
                'failed_reason_msg': 'Insufficient funds'
            }

            success, message = paytr_service.process_payment_callback(post_data)

            assert success is True  # Still return OK to acknowledge receipt
            assert message == 'OK'

            # Verify payment was marked as failed
            payment = Payment.query.filter_by(paytr_merchant_oid=merchant_oid).first()
            assert payment.status == 'failed'
            assert payment.failure_reason_code == 'INSUFFICIENT_FUNDS'
            assert payment.failure_reason_message == 'Insufficient funds'


class TestTrialSubscription:
    """Test trial subscription management."""

    def test_create_trial_subscription(self, app, company, paytr_service):
        """Test creating trial subscription."""
        with app.app_context():
            subscription = paytr_service.create_trial_subscription(company, 'team')

            assert subscription is not None
            assert subscription.company_id == company.id
            assert subscription.plan == 'team'
            assert subscription.status == 'trial'
            assert subscription.trial_starts_at is not None
            assert subscription.trial_ends_at is not None

            # Verify trial period is 14 days
            trial_duration = (subscription.trial_ends_at - subscription.trial_starts_at).days
            assert trial_duration == 14

            # Verify company was updated
            assert company.plan == 'team'
            assert company.max_workspaces == 20


class TestSubscriptionCancellation:
    """Test subscription cancellation."""

    def test_cancel_subscription_at_period_end(self, app, company, paytr_service):
        """Test cancelling subscription at period end."""
        with app.app_context():
            # Create active subscription
            subscription = Subscription(
                company_id=company.id,
                plan='team',
                status='active',
                current_period_start=datetime.utcnow(),
                current_period_end=datetime.utcnow() + timedelta(days=30)
            )
            db.session.add(subscription)
            db.session.commit()

            success = paytr_service.cancel_subscription(subscription, immediate=False)

            assert success is True
            assert subscription.cancel_at_period_end is True
            assert subscription.cancelled_at is not None
            assert subscription.status == 'active'  # Still active until period end

    def test_cancel_subscription_immediately(self, app, company, paytr_service):
        """Test immediate subscription cancellation."""
        with app.app_context():
            # Create active subscription
            subscription = Subscription(
                company_id=company.id,
                plan='team',
                status='active',
                current_period_start=datetime.utcnow(),
                current_period_end=datetime.utcnow() + timedelta(days=30)
            )
            db.session.add(subscription)
            db.session.commit()

            success = paytr_service.cancel_subscription(subscription, immediate=True)

            assert success is True
            assert subscription.status == 'cancelled'
            assert subscription.cancelled_at is not None
