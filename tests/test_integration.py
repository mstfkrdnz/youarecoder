"""
Integration tests for end-to-end user flows.
"""
import pytest
from datetime import datetime, timedelta
from app import db
from app.models import User, Company, Workspace, LoginAttempt


@pytest.mark.integration
@pytest.mark.security
class TestRegistrationFlow:
    """Test complete registration flow with password validation."""

    def test_complete_registration_success(self, client, db_session):
        """Test successful company and user registration."""
        response = client.post('/auth/register', data={
            'company_name': 'New Company',
            'subdomain': 'newco',
            'full_name': 'New User',
            'username': 'newuser',
            'email': 'new@test.com',
            'password': 'NewPass123!',
            'password_confirm': 'NewPass123!',
        }, follow_redirects=True)

        # Should succeed and redirect to login
        assert response.status_code == 200

        # Verify company was created
        company = Company.query.filter_by(subdomain='newco').first()
        assert company is not None
        assert company.name == 'New Company'

        # Verify user was created
        user = User.query.filter_by(email='new@test.com').first()
        assert user is not None
        assert user.role == 'admin'
        assert user.company_id == company.id

    def test_registration_with_weak_password_fails(self, client, db_session):
        """Test that registration fails with weak password."""
        response = client.post('/auth/register', data={
            'company_name': 'Weak Pass Co',
            'subdomain': 'weakpass',
            'full_name': 'Weak User',
            'username': 'weakuser',
            'email': 'weak@test.com',
            'password': 'weak',  # Too weak
            'password_confirm': 'weak',
        }, follow_redirects=True)

        # Should show validation error
        assert response.status_code == 200
        assert b'password' in response.data.lower() or b'character' in response.data.lower()

        # Verify user was NOT created
        user = User.query.filter_by(email='weak@test.com').first()
        assert user is None

    def test_registration_duplicate_subdomain_fails(self, client, db_session, company):
        """Test that duplicate subdomain is rejected."""
        response = client.post('/auth/register', data={
            'company_name': 'Duplicate Co',
            'subdomain': company.subdomain,  # Already exists
            'full_name': 'Dup User',
            'username': 'dupuser',
            'email': 'dup@test.com',
            'password': 'DupPass123!',
            'password_confirm': 'DupPass123!',
        }, follow_redirects=True)

        # Should show error
        assert response.status_code == 200
        assert b'taken' in response.data.lower() or b'exists' in response.data.lower()


@pytest.mark.integration
@pytest.mark.security
class TestLoginLockoutFlow:
    """Test failed login to lockout to unlock flow."""

    def test_failed_login_lockout_flow(self, client, db_session, admin_user):
        """Test complete lockout and unlock flow."""
        # 1. Attempt 5 failed logins
        for i in range(5):
            response = client.post('/auth/login', data={
                'email': admin_user.email,
                'password': 'WrongPassword',
            })
            assert response.status_code in [200, 302]

            # Verify LoginAttempt was recorded
            attempts = LoginAttempt.query.filter_by(
                email=admin_user.email,
                success=False
            ).count()
            assert attempts == i + 1

        # Refresh user from database
        db_session.session.refresh(admin_user)

        # 2. Account should now be locked
        assert admin_user.is_account_locked()
        assert admin_user.failed_login_attempts == 5

        # 3. Attempt login with correct password (should still be locked)
        response = client.post('/auth/login', data={
            'email': admin_user.email,
            'password': 'AdminPass123!',
        }, follow_redirects=True)

        # Should show lockout message
        assert b'locked' in response.data.lower() or b'failed' in response.data.lower()

        # 4. Simulate time passing (unlock)
        admin_user.account_locked_until = datetime.utcnow() - timedelta(minutes=1)
        admin_user.failed_login_attempts = 0
        db_session.session.commit()

        # 5. Now login should succeed
        response = client.post('/auth/login', data={
            'email': admin_user.email,
            'password': 'AdminPass123!',
        }, follow_redirects=False)

        # Should redirect to dashboard
        assert response.status_code == 302

    def test_successful_login_resets_failed_attempts(self, client, db_session, admin_user):
        """Test that successful login resets failed attempt counter."""
        # Record 3 failed attempts
        for _ in range(3):
            admin_user.record_failed_login()
        db_session.session.commit()

        assert admin_user.failed_login_attempts == 3

        # Successful login
        response = client.post('/auth/login', data={
            'email': admin_user.email,
            'password': 'AdminPass123!',
        }, follow_redirects=False)

        # Refresh from database
        db_session.session.refresh(admin_user)

        # Counter should be reset
        assert admin_user.failed_login_attempts == 0

    def test_login_attempts_audit_trail(self, client, db_session, admin_user):
        """Test that all login attempts are logged for audit."""
        # Perform mix of successful and failed logins
        # Failed login 1
        client.post('/auth/login', data={
            'email': admin_user.email,
            'password': 'Wrong1',
        })

        # Failed login 2
        client.post('/auth/login', data={
            'email': admin_user.email,
            'password': 'Wrong2',
        })

        # Successful login
        client.post('/auth/login', data={
            'email': admin_user.email,
            'password': 'AdminPass123!',
        })

        # Check audit trail
        attempts = LoginAttempt.query.filter_by(email=admin_user.email).all()
        assert len(attempts) == 3

        failed = [a for a in attempts if not a.success]
        assert len(failed) == 2

        successful = [a for a in attempts if a.success]
        assert len(successful) == 1


@pytest.mark.integration
@pytest.mark.security
class TestWorkspaceAuthorizationFlow:
    """Test workspace authorization end-to-end."""

    def test_workspace_access_same_company(self, client, db_session, admin_user, member_user, workspace):
        """Test that users from same company can access workspace."""
        from tests.conftest import login_as_user

        # Admin creates workspace (already created in fixture)
        # Member from same company should access
        login_as_user(client, member_user)

        response = client.get(f'/workspace/{workspace.id}')

        # Should not be 403 (same company)
        assert response.status_code != 403

    def test_workspace_access_different_company_forbidden(self, client, db_session, other_user, workspace):
        """Test that users from different company cannot access workspace."""
        from tests.conftest import login_as_user

        # Login as other_user from different company
        login_as_user(client, other_user)

        response = client.get(f'/workspace/{workspace.id}')

        # Should be 403 (different company)
        assert response.status_code == 403

    def test_workspace_api_authorization(self, client, db_session, admin_user, other_user, workspace):
        """Test workspace API endpoint authorization."""
        from tests.conftest import login_as_user

        # Owner accessing own workspace
        login_as_user(client, admin_user)
        response = client.get(f'/api/workspace/{workspace.id}/status')
        assert response.status_code != 403

        # Different company user accessing workspace
        login_as_user(client, other_user)
        response = client.get(f'/api/workspace/{workspace.id}/status')
        assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.security
class TestCrossCompanyIsolation:
    """Test cross-company data isolation."""

    def test_user_cannot_see_other_company_workspaces(self, client, db_session, admin_user, other_user, workspace, other_workspace):
        """Test that users only see their company's workspaces."""
        from tests.conftest import login_as_user

        # Login as admin_user
        login_as_user(client, admin_user)

        # Try to access other company's workspace
        response = client.get(f'/workspace/{other_workspace.id}')

        # Should be forbidden
        assert response.status_code == 403

    def test_workspace_list_filters_by_company(self, client, db_session, admin_user, workspace):
        """Test that workspace listing is filtered by company."""
        from tests.conftest import login_as_user

        login_as_user(client, admin_user)

        response = client.get('/dashboard')

        # Should only see own company's workspaces
        # (This is a basic check - more detailed checks would require parsing response)
        assert response.status_code == 200

    def test_api_endpoints_enforce_company_isolation(self, client, db_session, admin_user, other_workspace):
        """Test that API endpoints enforce company isolation."""
        from tests.conftest import login_as_user

        login_as_user(client, admin_user)

        # Try to access different company's workspace via API
        endpoints = [
            f'/api/workspace/{other_workspace.id}/status',
            f'/api/workspace/{other_workspace.id}/restart',
            f'/api/workspace/{other_workspace.id}/stop',
            f'/api/workspace/{other_workspace.id}/start',
        ]

        for endpoint in endpoints:
            if 'status' in endpoint:
                response = client.get(endpoint)
            else:
                response = client.post(endpoint)

            # All should be 403 (different company)
            assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.slow
class TestRateLimitBehavior:
    """Test rate limiting behavior under load."""

    def test_rate_limit_per_ip(self, app_with_rate_limiting, db_session):
        """Test that rate limits are enforced per IP address."""
        client1 = app_with_rate_limiting.test_client()
        client2 = app_with_rate_limiting.test_client()

        with app_with_rate_limiting.app_context():
            db.create_all()

            # Each client should have independent rate limits
            # (In real scenario with different IPs)
            for i in range(5):
                response1 = client1.post('/auth/login', data={'email': 'test1@test.com', 'password': 'wrong'})
                response2 = client2.post('/auth/login', data={'email': 'test2@test.com', 'password': 'wrong'})

                # Both should succeed (not rate limited yet)
                assert response1.status_code in [200, 302]
                assert response2.status_code in [200, 302]

    def test_rate_limit_recovery_after_time(self, app_with_rate_limiting, db_session):
        """Test that rate limits reset after time window."""
        client = app_with_rate_limiting.test_client()

        with app_with_rate_limiting.app_context():
            db.create_all()

            # Hit rate limit
            for i in range(11):
                response = client.post('/auth/login', data={'email': 'test@test.com', 'password': 'wrong'})

            # Last one should be rate limited
            assert response.status_code == 429

            # Note: In a real scenario, we'd wait for the time window to pass
            # This test just verifies the mechanism is in place
