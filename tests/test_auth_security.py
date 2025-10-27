"""
Tests for authentication security features.
"""
import pytest
from datetime import datetime, timedelta
from app import db
from app.models import User, Company, LoginAttempt
from app.forms import RegistrationForm


@pytest.mark.unit
@pytest.mark.security
class TestPasswordComplexity:
    """Test password complexity validation."""

    def test_password_too_short(self, app):
        """Test that passwords under 8 characters are rejected."""
        with app.app_context():
            form = RegistrationForm(
                company_name='Test Co',
                subdomain='testco',
                full_name='Test User',
                username='testuser',
                email='test@test.com',
                password='Short1!',  # Only 7 chars
                password_confirm='Short1!'
            )
            assert not form.validate()
            assert any('8 characters' in str(error) for error in form.password.errors)

    def test_password_missing_uppercase(self, app):
        """Test that passwords without uppercase are rejected."""
        with app.app_context():
            form = RegistrationForm(
                company_name='Test Co',
                subdomain='testco',
                full_name='Test User',
                username='testuser',
                email='test@test.com',
                password='lowercase123!',  # No uppercase
                password_confirm='lowercase123!'
            )
            assert not form.validate()
            assert any('uppercase' in str(error).lower() for error in form.password.errors)

    def test_password_missing_lowercase(self, app):
        """Test that passwords without lowercase are rejected."""
        with app.app_context():
            form = RegistrationForm(
                company_name='Test Co',
                subdomain='testco',
                full_name='Test User',
                username='testuser',
                email='test@test.com',
                password='UPPERCASE123!',  # No lowercase
                password_confirm='UPPERCASE123!'
            )
            assert not form.validate()
            assert any('lowercase' in str(error).lower() for error in form.password.errors)

    def test_password_missing_digit(self, app):
        """Test that passwords without digits are rejected."""
        with app.app_context():
            form = RegistrationForm(
                company_name='Test Co',
                subdomain='testco',
                full_name='Test User',
                username='testuser',
                email='test@test.com',
                password='NoDigits!',  # No digit
                password_confirm='NoDigits!'
            )
            assert not form.validate()
            assert any('digit' in str(error).lower() for error in form.password.errors)

    def test_password_missing_special_char(self, app):
        """Test that passwords without special characters are rejected."""
        with app.app_context():
            form = RegistrationForm(
                company_name='Test Co',
                subdomain='testco',
                full_name='Test User',
                username='testuser',
                email='test@test.com',
                password='NoSpecial123',  # No special char
                password_confirm='NoSpecial123'
            )
            assert not form.validate()
            assert any('special character' in str(error).lower() for error in form.password.errors)

    def test_password_valid_complex(self, app):
        """Test that complex passwords are accepted."""
        with app.app_context():
            form = RegistrationForm(
                company_name='Test Co',
                subdomain='testco',
                full_name='Test User',
                username='testuser',
                email='test@test.com',
                password='ValidPass123!',  # Meets all requirements
                password_confirm='ValidPass123!'
            )
            # Should not have password validation errors
            form.validate()
            password_errors = [e for e in form.password.errors if 'character' in str(e).lower() or 'digit' in str(e).lower()]
            assert len(password_errors) == 0


@pytest.mark.unit
@pytest.mark.security
class TestFailedLoginTracking:
    """Test failed login attempt tracking."""

    def test_record_failed_login_increments(self, db_session, admin_user):
        """Test that failed login attempts are incremented."""
        assert admin_user.failed_login_attempts == 0

        admin_user.record_failed_login()
        db_session.session.commit()

        assert admin_user.failed_login_attempts == 1

    def test_multiple_failed_logins(self, db_session, admin_user):
        """Test multiple failed login attempts."""
        for i in range(3):
            admin_user.record_failed_login()
            db_session.session.commit()
            assert admin_user.failed_login_attempts == i + 1

    def test_account_locked_after_threshold(self, db_session, admin_user):
        """Test that account is locked after 5 failed attempts."""
        assert not admin_user.is_account_locked()

        # Record 5 failed attempts
        for _ in range(5):
            admin_user.record_failed_login()

        db_session.session.commit()

        assert admin_user.is_account_locked()
        assert admin_user.account_locked_until is not None

    def test_lockout_duration_30_minutes(self, db_session, admin_user):
        """Test that lockout duration is 30 minutes."""
        # Record 5 failed attempts to trigger lockout
        for _ in range(5):
            admin_user.record_failed_login()

        db_session.session.commit()

        # Check lockout time is approximately 30 minutes from now
        lockout_duration = admin_user.account_locked_until - datetime.utcnow()
        assert 29 * 60 < lockout_duration.total_seconds() < 31 * 60  # 29-31 minutes

    def test_reset_failed_logins(self, db_session, admin_user):
        """Test that failed login counter is reset."""
        # Record some failed attempts
        for _ in range(3):
            admin_user.record_failed_login()

        db_session.session.commit()
        assert admin_user.failed_login_attempts == 3

        # Reset
        admin_user.reset_failed_logins()
        db_session.session.commit()

        assert admin_user.failed_login_attempts == 0
        assert admin_user.account_locked_until is None

    def test_successful_login_resets_counter(self, client, db_session, admin_user):
        """Test that successful login resets failed attempt counter."""
        # Record some failed attempts
        for _ in range(3):
            admin_user.record_failed_login()

        db_session.session.commit()
        assert admin_user.failed_login_attempts == 3

        # Successful login
        response = client.post('/auth/login', data={
            'email': admin_user.email,
            'password': 'AdminPass123!',
        }, follow_redirects=False)

        db_session.session.refresh(admin_user)
        assert admin_user.failed_login_attempts == 0


@pytest.mark.unit
@pytest.mark.security
class TestAccountLockout:
    """Test account lockout mechanism."""

    def test_is_account_locked_before_threshold(self, db_session, admin_user):
        """Test that account is not locked before 5 attempts."""
        for _ in range(4):
            admin_user.record_failed_login()

        db_session.session.commit()
        assert not admin_user.is_account_locked()

    def test_is_account_locked_at_threshold(self, db_session, admin_user):
        """Test that account is locked at exactly 5 attempts."""
        for _ in range(5):
            admin_user.record_failed_login()

        db_session.session.commit()
        assert admin_user.is_account_locked()

    def test_locked_account_prevents_login(self, client, db_session, admin_user):
        """Test that locked account cannot login."""
        # Lock the account
        for _ in range(5):
            admin_user.record_failed_login()

        db_session.session.commit()

        # Try to login
        response = client.post('/auth/login', data={
            'email': admin_user.email,
            'password': 'AdminPass123!',
        }, follow_redirects=True)

        # Should show lockout message
        assert response.status_code == 200
        assert b'locked' in response.data.lower() or b'multiple failed' in response.data.lower()

    def test_lockout_expires_after_duration(self, db_session, admin_user):
        """Test that lockout expires after 30 minutes."""
        # Manually set lockout to 31 minutes ago
        admin_user.failed_login_attempts = 5
        admin_user.account_locked_until = datetime.utcnow() - timedelta(minutes=31)
        db_session.session.commit()

        # Account should not be locked anymore
        assert not admin_user.is_account_locked()

    def test_lockout_active_before_expiration(self, db_session, admin_user):
        """Test that lockout is active before expiration time."""
        # Set lockout to 10 minutes from now
        admin_user.failed_login_attempts = 5
        admin_user.account_locked_until = datetime.utcnow() + timedelta(minutes=10)
        db_session.session.commit()

        # Account should still be locked
        assert admin_user.is_account_locked()


@pytest.mark.unit
@pytest.mark.security
class TestLoginAttemptModel:
    """Test LoginAttempt audit logging."""

    def test_create_login_attempt(self, db_session):
        """Test creating login attempt record."""
        attempt = LoginAttempt(
            email='test@test.com',
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0',
            success=False,
            failure_reason='invalid_password'
        )
        db_session.session.add(attempt)
        db_session.session.commit()

        assert attempt.id is not None
        assert attempt.timestamp is not None

    def test_login_attempt_tracks_ip(self, db_session):
        """Test that IP address is tracked."""
        attempt = LoginAttempt(
            email='test@test.com',
            ip_address='10.0.0.1',
            success=True
        )
        db_session.session.add(attempt)
        db_session.session.commit()

        assert attempt.ip_address == '10.0.0.1'

    def test_login_attempt_tracks_user_agent(self, db_session):
        """Test that user agent is tracked."""
        user_agent = 'Mozilla/5.0 (X11; Linux x86_64)'
        attempt = LoginAttempt(
            email='test@test.com',
            ip_address='127.0.0.1',
            user_agent=user_agent,
            success=True
        )
        db_session.session.add(attempt)
        db_session.session.commit()

        assert attempt.user_agent == user_agent

    def test_login_attempt_failure_reasons(self, db_session):
        """Test different failure reasons are recorded."""
        reasons = ['invalid_password', 'account_locked', 'inactive_account', 'invalid_email']

        for reason in reasons:
            attempt = LoginAttempt(
                email=f'{reason}@test.com',
                ip_address='127.0.0.1',
                success=False,
                failure_reason=reason
            )
            db_session.session.add(attempt)

        db_session.session.commit()

        attempts = LoginAttempt.query.all()
        recorded_reasons = [a.failure_reason for a in attempts]
        for reason in reasons:
            assert reason in recorded_reasons

    def test_successful_login_attempt_no_failure_reason(self, db_session):
        """Test that successful logins have no failure reason."""
        attempt = LoginAttempt(
            email='success@test.com',
            ip_address='127.0.0.1',
            success=True
        )
        db_session.session.add(attempt)
        db_session.session.commit()

        assert attempt.success is True
        assert attempt.failure_reason is None

    def test_query_attempts_by_email(self, db_session):
        """Test querying login attempts by email."""
        # Create multiple attempts for same email
        for i in range(3):
            attempt = LoginAttempt(
                email='user@test.com',
                ip_address='127.0.0.1',
                success=i == 2  # Last one successful
            )
            db_session.session.add(attempt)

        db_session.session.commit()

        attempts = LoginAttempt.query.filter_by(email='user@test.com').all()
        assert len(attempts) == 3

    def test_query_failed_attempts(self, db_session):
        """Test querying only failed login attempts."""
        # Create mix of successful and failed attempts
        for i in range(5):
            attempt = LoginAttempt(
                email=f'user{i}@test.com',
                ip_address='127.0.0.1',
                success=i % 2 == 0  # Alternate success/fail
            )
            db_session.session.add(attempt)

        db_session.session.commit()

        failed = LoginAttempt.query.filter_by(success=False).all()
        assert len(failed) == 2  # Indices 1 and 3
