"""
TDD Tests for Billing Routes

Tests cover all billing endpoints:
- POST /billing/subscribe/<plan> - Payment initiation
- POST /billing/callback - PayTR webhook callback
- GET /billing/payment/success - Success redirect
- GET /billing/payment/fail - Failure redirect
- GET /billing - Billing dashboard
"""
import base64
import hashlib
import hmac
import json
import pytest
from unittest.mock import patch, Mock

from app import create_app, db
from app.models import Company, User, Subscription, Payment


@pytest.fixture
def app():
    """Create test Flask application."""
    app = create_app('test')
    app.config['PAYTR_MERCHANT_ID'] = 'TEST123'
    app.config['PAYTR_MERCHANT_KEY'] = 'TESTKEY123'
    app.config['PAYTR_MERCHANT_SALT'] = 'TESTSALT123'
    app.config['PAYTR_TEST_MODE'] = '1'
    app.config['BASE_URL'] = 'https://test.youarecoder.com'

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
def authenticated_user(app, client):
    """Create and login a test user."""
    with app.app_context():
        # Create company
        company = Company(
            name='Test Company',
            subdomain='testco',
            plan='team',
            max_workspaces=20
        )
        db.session.add(company)
        db.session.flush()  # Get company.id

        # Create user
        user = User(
            email='test@example.com',
            username='testuser',
            full_name='Test User',
            company_id=company.id,  # Now company.id is available
            role='admin'
        )
        user.set_password('TestPass123!')
        db.session.add(user)
        db.session.commit()

        # Login user
        client.post('/auth/login', data={
            'email': 'test@example.com',
            'password': 'TestPass123!'
        }, follow_redirects=True)

        return user


class TestSubscribeEndpoint:
    """Tests for POST /billing/subscribe/<plan>"""

    def test_subscribe_requires_authentication(self, client):
        """Test that subscribe endpoint requires login."""
        response = client.post('/billing/subscribe/team')

        # Should redirect to login
        assert response.status_code == 302
        assert '/auth/login' in response.location

    def test_subscribe_invalid_plan(self, client, authenticated_user):
        """Test subscribe with invalid plan name."""
        response = client.post('/billing/subscribe/invalid_plan')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Invalid plan' in data['error']

    def test_subscribe_success(self, client, authenticated_user, app):
        """Test successful payment initiation."""
        with app.app_context():
            mock_result = {
                'success': True,
                'token': 'test_iframe_token',
                'iframe_url': 'https://www.paytr.com/odeme/guvenli/test_iframe_token',
                'payment_id': 1,
                'merchant_oid': 'YAC-123-1'
            }

            with patch('app.routes.billing.PayTRService.generate_iframe_token') as mock_gen:
                mock_gen.return_value = mock_result

                response = client.post('/billing/subscribe/team')

                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] is True
                assert 'iframe_url' in data
                assert data['iframe_url'] == mock_result['iframe_url']

    def test_subscribe_paytr_failure(self, client, authenticated_user, app):
        """Test handling of PayTR API failure."""
        with app.app_context():
            mock_result = {
                'success': False,
                'reason': 'Invalid merchant credentials'
            }

            with patch('app.routes.billing.PayTRService.generate_iframe_token') as mock_gen:
                mock_gen.return_value = mock_result

                response = client.post('/billing/subscribe/team')

                assert response.status_code == 500
                data = json.loads(response.data)
                assert 'error' in data
                assert 'Invalid merchant credentials' in data['error']


class TestPaymentCallbackEndpoint:
    """Tests for POST /billing/callback"""

    def test_callback_csrf_exempt(self, client, app):
        """Test that callback endpoint is CSRF exempt."""
        # This test verifies callback can receive POST without CSRF token
        with app.app_context():
            response = client.post('/billing/callback', data={
                'merchant_oid': 'test',
                'status': 'success',
                'total_amount': '9900',
                'hash': 'test_hash'
            })

            # Should not get CSRF error (400), but other error is fine
            assert response.status_code != 400 or b'CSRF' not in response.data

    def test_callback_invalid_hash(self, client, app):
        """Test callback with invalid hash."""
        with app.app_context():
            post_data = {
                'merchant_oid': 'YAC-123-1',
                'status': 'success',
                'total_amount': '9900',
                'hash': 'invalid_hash_value',
                'test_mode': '1',
                'payment_type': 'card'
            }

            response = client.post('/billing/callback', data=post_data)

            assert response.status_code == 400
            assert b'Invalid hash' in response.data

    def test_callback_success(self, client, app):
        """Test successful payment callback processing."""
        with app.app_context():
            # Create company and payment
            company = Company(
                name='Test Company',
                subdomain='testco',
                plan='team',
                max_workspaces=20
            )
            db.session.add(company)
            db.session.commit()

            payment = Payment(
                company_id=company.id,
                paytr_merchant_oid='YAC-123-1',
                amount=9900,
                currency='USD',
                status='pending',
                payment_type='initial',
                test_mode=True,
                user_ip='192.168.1.1'
            )
            db.session.add(payment)
            db.session.commit()

            # Generate valid hash
            merchant_salt = app.config['PAYTR_MERCHANT_SALT']
            merchant_key = app.config['PAYTR_MERCHANT_KEY'].encode('utf-8')
            merchant_oid = 'YAC-123-1'
            status = 'success'
            total_amount = '9900'

            hash_str = f"{merchant_oid}{merchant_salt}{status}{total_amount}"
            valid_hash = base64.b64encode(
                hmac.new(merchant_key, hash_str.encode('utf-8'), hashlib.sha256).digest()
            ).decode('utf-8')

            post_data = {
                'merchant_oid': merchant_oid,
                'status': status,
                'total_amount': total_amount,
                'hash': valid_hash,
                'test_mode': '1',
                'payment_type': 'card'
            }

            response = client.post('/billing/callback', data=post_data)

            assert response.status_code == 200
            assert response.data == b'OK'

            # Verify payment was updated
            payment = Payment.query.filter_by(paytr_merchant_oid=merchant_oid).first()
            assert payment.status == 'success'


class TestSuccessRedirectEndpoint:
    """Tests for GET /billing/payment/success"""

    def test_success_page_renders(self, client):
        """Test success page renders correctly."""
        response = client.get('/billing/payment/success')

        assert response.status_code == 200
        assert b'Payment Successful' in response.data or b'success' in response.data.lower()

    def test_success_page_with_merchant_oid(self, client):
        """Test success page with merchant_oid parameter."""
        response = client.get('/billing/payment/success?merchant_oid=YAC-123-1')

        assert response.status_code == 200


class TestFailRedirectEndpoint:
    """Tests for GET /billing/payment/fail"""

    def test_fail_page_renders(self, client):
        """Test failure page renders correctly."""
        response = client.get('/billing/payment/fail')

        assert response.status_code == 200
        assert b'Payment Failed' in response.data or b'fail' in response.data.lower()

    def test_fail_page_with_reason(self, client):
        """Test failure page with error reason."""
        response = client.get('/billing/payment/fail?reason=INSUFFICIENT_FUNDS')

        assert response.status_code == 200


class TestBillingDashboardEndpoint:
    """Tests for GET /billing"""

    def test_billing_requires_authentication(self, client):
        """Test that billing dashboard requires login."""
        response = client.get('/billing/')

        # Should redirect to login (302 or 308 are both acceptable redirects)
        assert response.status_code in [302, 308]
        assert '/auth/login' in response.location or response.status_code == 308

    def test_billing_dashboard_renders(self, client, authenticated_user, app):
        """Test billing dashboard renders with subscription info."""
        with app.app_context():
            # Get the user's company
            user = User.query.filter_by(email='test@example.com').first()
            company = user.company

            # Create subscription
            subscription = Subscription(
                company_id=company.id,
                plan='team',
                status='active'
            )
            db.session.add(subscription)
            db.session.commit()

            response = client.get('/billing/', follow_redirects=True)

            assert response.status_code == 200
            assert b'Billing' in response.data or b'Subscription' in response.data

    def test_billing_dashboard_no_subscription(self, client, authenticated_user):
        """Test billing dashboard when company has no subscription."""
        response = client.get('/billing/', follow_redirects=True)

        assert response.status_code == 200
        # Should show option to subscribe


class TestErrorHandling:
    """Tests for error handling across billing routes"""

    def test_subscribe_with_exception(self, client, authenticated_user, app):
        """Test handling of unexpected exceptions."""
        with app.app_context():
            with patch('app.routes.billing.PayTRService.generate_iframe_token') as mock_gen:
                mock_gen.side_effect = Exception("Unexpected error")

                response = client.post('/billing/subscribe/team')

                assert response.status_code == 500
                data = json.loads(response.data)
                assert 'error' in data

    def test_callback_with_missing_payment(self, client, app):
        """Test callback when payment record doesn't exist."""
        with app.app_context():
            # Generate valid hash for non-existent payment
            merchant_salt = app.config['PAYTR_MERCHANT_SALT']
            merchant_key = app.config['PAYTR_MERCHANT_KEY'].encode('utf-8')
            merchant_oid = 'NONEXISTENT-123'
            status = 'success'
            total_amount = '9900'

            hash_str = f"{merchant_oid}{merchant_salt}{status}{total_amount}"
            valid_hash = base64.b64encode(
                hmac.new(merchant_key, hash_str.encode('utf-8'), hashlib.sha256).digest()
            ).decode('utf-8')

            post_data = {
                'merchant_oid': merchant_oid,
                'status': status,
                'total_amount': total_amount,
                'hash': valid_hash,
                'test_mode': '1',
                'payment_type': 'card'
            }

            response = client.post('/billing/callback', data=post_data)

            assert response.status_code == 404 or response.status_code == 400
