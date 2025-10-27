"""
Tests for rate limiting on sensitive endpoints.
"""
import pytest
from time import sleep
from app import db


@pytest.mark.unit
@pytest.mark.security
class TestLoginRateLimiting:
    """Test rate limiting on login endpoint."""

    def test_login_rate_limit_10_per_minute(self, app_with_rate_limiting):
        """Test that login endpoint is limited to 10 requests per minute."""
        client = app_with_rate_limiting.test_client()

        with app_with_rate_limiting.app_context():
            from app.models import Company, User
            db.create_all()

            # Create company and user in this app's context
            company = Company(name='Test Co', subdomain='testco', plan='starter', max_workspaces=3)
            db.session.add(company)
            db.session.commit()

            user = User(email='admin@test.com', username='admin', full_name='Admin', role='admin', company_id=company.id)
            user.set_password('AdminPass123!')
            db.session.add(user)
            db.session.commit()

            # Make 10 requests (should succeed)
            for i in range(10):
                response = client.post('/auth/login', data={
                    'email': 'test@test.com',
                    'password': 'wrong',
                })
                assert response.status_code in [200, 302]  # Not rate limited

            # 11th request should be rate limited
            response = client.post('/auth/login', data={
                'email': 'test@test.com',
                'password': 'wrong',
            })
            assert response.status_code == 429  # Too Many Requests

    def test_login_rate_limit_headers(self, app_with_rate_limiting):
        """Test that rate limit headers are present."""
        client = app_with_rate_limiting.test_client()

        with app_with_rate_limiting.app_context():
            db.create_all()

            response = client.post('/auth/login', data={
                'email': 'test@test.com',
                'password': 'wrong',
            })

            # Check for rate limit headers
            assert 'X-RateLimit-Limit' in response.headers or 'RateLimit-Limit' in response.headers


@pytest.mark.unit
@pytest.mark.security
class TestRegistrationRateLimiting:
    """Test rate limiting on registration endpoint."""

    def test_register_rate_limit_5_per_hour(self, app_with_rate_limiting):
        """Test that registration endpoint is limited to 5 requests per hour."""
        client = app_with_rate_limiting.test_client()

        with app_with_rate_limiting.app_context():
            db.create_all()

            # Make 5 requests (should succeed or fail on validation, not rate limit)
            for i in range(5):
                response = client.post('/auth/register', data={
                    'company_name': f'Company {i}',
                    'subdomain': f'co{i}',
                    'full_name': 'Test User',
                    'username': f'user{i}',
                    'email': f'test{i}@test.com',
                    'password': 'TestPass123!',
                    'password_confirm': 'TestPass123!',
                })
                # Should not be rate limited (may fail validation)
                assert response.status_code != 429

            # 6th request should be rate limited
            response = client.post('/auth/register', data={
                'company_name': 'Company 6',
                'subdomain': 'co6',
                'full_name': 'Test User',
                'username': 'user6',
                'email': 'test6@test.com',
                'password': 'TestPass123!',
                'password_confirm': 'TestPass123!',
            })
            assert response.status_code == 429  # Too Many Requests


@pytest.mark.unit
@pytest.mark.security
class TestAPIRateLimiting:
    """Test rate limiting on API endpoints."""

    def test_workspace_restart_rate_limit(self, app_with_rate_limiting):
        """Test that workspace restart is limited to 5 per minute."""
        client = app_with_rate_limiting.test_client()

        with app_with_rate_limiting.app_context():
            from app.models import Company, User, Workspace
            db.create_all()

            # Create company, user, and workspace in this app's context
            company = Company(name='Test Co', subdomain='testco',  plan='starter', max_workspaces=3)
            db.session.add(company)
            db.session.commit()

            user = User(email='admin@test.com', username='admin', full_name='Admin', role='admin', company_id=company.id)
            user.set_password('AdminPass123!')
            db.session.add(user)
            db.session.commit()

            workspace = Workspace(name='test-ws', subdomain='testco-test', linux_username='testco_test',
                                port=8001, code_server_password='test', status='active',
                                company_id=company.id, owner_id=user.id)
            db.session.add(workspace)
            db.session.commit()

            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)

            # Make 5 requests (should succeed or fail, but not rate limited)
            for i in range(5):
                response = client.post(f'/api/workspace/{workspace.id}/restart')
                assert response.status_code != 429

            # 6th request should be rate limited
            response = client.post(f'/api/workspace/{workspace.id}/restart')
            assert response.status_code == 429

    def test_workspace_stop_rate_limit(self, app_with_rate_limiting):
        """Test that workspace stop is limited to 5 per minute."""
        client = app_with_rate_limiting.test_client()

        with app_with_rate_limiting.app_context():
            from app.models import Company, User, Workspace
            db.create_all()

            # Create company, user, and workspace in this app's context
            company = Company(name='Test Co', subdomain='testco',  plan='starter', max_workspaces=3)
            db.session.add(company)
            db.session.commit()

            user = User(email='admin@test.com', username='admin', full_name='Admin', role='admin', company_id=company.id)
            user.set_password('AdminPass123!')
            db.session.add(user)
            db.session.commit()

            workspace = Workspace(name='test-ws', subdomain='testco-test', linux_username='testco_test',
                                port=8001, code_server_password='test', status='active',
                                company_id=company.id, owner_id=user.id)
            db.session.add(workspace)
            db.session.commit()

            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)

            # Make 5 requests
            for i in range(5):
                response = client.post(f'/api/workspace/{workspace.id}/stop')
                assert response.status_code != 429

            # 6th request should be rate limited
            response = client.post(f'/api/workspace/{workspace.id}/stop')
            assert response.status_code == 429

    def test_workspace_start_rate_limit(self, app_with_rate_limiting):
        """Test that workspace start is limited to 5 per minute."""
        client = app_with_rate_limiting.test_client()

        with app_with_rate_limiting.app_context():
            from app.models import Company, User, Workspace
            db.create_all()

            # Create company, user, and workspace in this app's context
            company = Company(name='Test Co', subdomain='testco',  plan='starter', max_workspaces=3)
            db.session.add(company)
            db.session.commit()

            user = User(email='admin@test.com', username='admin', full_name='Admin', role='admin', company_id=company.id)
            user.set_password('AdminPass123!')
            db.session.add(user)
            db.session.commit()

            workspace = Workspace(name='test-ws', subdomain='testco-test', linux_username='testco_test',
                                port=8001, code_server_password='test', status='active',
                                company_id=company.id, owner_id=user.id)
            db.session.add(workspace)
            db.session.commit()

            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)

            # Make 5 requests
            for i in range(5):
                response = client.post(f'/api/workspace/{workspace.id}/start')
                assert response.status_code != 429

            # 6th request should be rate limited
            response = client.post(f'/api/workspace/{workspace.id}/start')
            assert response.status_code == 429


@pytest.mark.unit
@pytest.mark.security
class TestGlobalRateLimiting:
    """Test global rate limiting defaults."""

    def test_global_rate_limit_exists(self, app_with_rate_limiting):
        """Test that global rate limiting is configured."""
        # Check that limiter is configured
        assert app_with_rate_limiting.config.get('RATELIMIT_ENABLED') is True

    def test_rate_limit_storage_configured(self, app_with_rate_limiting):
        """Test that rate limit storage is configured."""
        # Should have memory storage configured
        storage_url = app_with_rate_limiting.config.get('RATELIMIT_STORAGE_URL')
        assert storage_url is not None
