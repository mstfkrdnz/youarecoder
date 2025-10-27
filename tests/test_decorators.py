"""
Tests for authorization decorators.
"""
import pytest
from flask import Flask, Blueprint
from flask_login import login_user, current_user
from app import create_app, db
from app.models import User, Company, Workspace
from app.utils.decorators import require_workspace_ownership, require_role, require_company_admin


@pytest.fixture
def fresh_app_for_routes():
    """Create a fresh Flask app for dynamic route testing."""
    app = create_app('test')
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key',
    })

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.mark.unit
@pytest.mark.security
class TestRequireWorkspaceOwnership:
    """Test @require_workspace_ownership decorator."""

    def test_owner_can_access_workspace(self, client, db_session, admin_user, workspace, authenticated_client):
        """Test that workspace owner can access their workspace."""
        response = authenticated_client.get(f'/workspace/{workspace.id}')
        # Should not get 403 Forbidden
        assert response.status_code in [200, 302, 404]  # Any except 403

    def test_same_company_user_can_access(self, client, db_session, member_user, workspace):
        """Test that users from same company can access workspace."""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(member_user.id)

        response = client.get(f'/workspace/{workspace.id}')
        # Same company should have access
        assert response.status_code != 403

    def test_different_company_user_forbidden(self, client, db_session, other_user, workspace):
        """Test that users from different company get 403."""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(other_user.id)

        response = client.get(f'/workspace/{workspace.id}')
        # Different company should be forbidden
        assert response.status_code == 403

    def test_nonexistent_workspace_404(self, client, db_session, admin_user, authenticated_client):
        """Test that non-existent workspace returns 404."""
        response = authenticated_client.get('/workspace/9999')
        assert response.status_code == 404

    def test_unauthenticated_user_redirected(self, client, db_session, workspace):
        """Test that unauthenticated users are redirected to login."""
        response = client.get(f'/workspace/{workspace.id}')
        # Should redirect to login (302) or get 401
        assert response.status_code in [302, 401]


@pytest.mark.unit
@pytest.mark.security
class TestRequireRole:
    """Test @require_role decorator."""

    def test_admin_role_access(self, app, db_session, admin_user):
        """Test that admin role can access admin-only routes."""
        @app.route('/test-admin')
        @require_role('admin')
        def admin_route():
            return 'admin access'

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['_user_id'] = str(admin_user.id)

            response = client.get('/test-admin')
            # Admin should have access
            assert response.status_code != 403

    def test_member_role_forbidden_from_admin_route(self, app, db_session, member_user):
        """Test that member role gets 403 on admin-only routes."""
        @app.route('/test-admin-only')
        @require_role('admin')
        def admin_only_route():
            return 'admin only'

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['_user_id'] = str(member_user.id)

            response = client.get('/test-admin-only')
            # Member should be forbidden
            assert response.status_code == 403

    def test_multiple_roles_allowed(self, app, db_session, admin_user, member_user):
        """Test that multiple roles can be allowed."""
        @app.route('/test-multi-role')
        @require_role('admin', 'member')
        def multi_role_route():
            return 'multi role access'

        with app.test_client() as client:
            # Test admin
            with client.session_transaction() as sess:
                sess['_user_id'] = str(admin_user.id)
            response = client.get('/test-multi-role')
            assert response.status_code != 403

            # Test member
            with client.session_transaction() as sess:
                sess['_user_id'] = str(member_user.id)
            response = client.get('/test-multi-role')
            assert response.status_code != 403


@pytest.mark.unit
@pytest.mark.security
class TestRequireCompanyAdmin:
    """Test @require_company_admin decorator."""

    def test_admin_can_access(self, app, db_session, admin_user):
        """Test that company admin can access admin routes."""
        @app.route('/test-company-admin')
        @require_company_admin
        def company_admin_route():
            return 'company admin access'

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['_user_id'] = str(admin_user.id)

            response = client.get('/test-company-admin')
            # Admin should have access
            assert response.status_code != 403

    def test_member_forbidden(self, app, db_session, member_user):
        """Test that non-admin member gets 403."""
        @app.route('/test-company-admin-forbidden')
        @require_company_admin
        def company_admin_forbidden_route():
            return 'company admin only'

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['_user_id'] = str(member_user.id)

            response = client.get('/test-company-admin-forbidden')
            # Member should be forbidden
            assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.security
class TestDecoratorIntegration:
    """Integration tests for decorator combinations."""

    def test_workspace_api_authorization(self, client, db_session, admin_user, other_user, workspace, other_workspace):
        """Test workspace API endpoint authorization."""
        # Admin accessing own workspace - should work
        with client.session_transaction() as sess:
            sess['_user_id'] = str(admin_user.id)

        response = client.get(f'/api/workspace/{workspace.id}/status')
        assert response.status_code in [200, 404]  # Not 403

        # Other user accessing different company workspace - should be 403
        with client.session_transaction() as sess:
            sess['_user_id'] = str(other_user.id)

        response = client.get(f'/api/workspace/{workspace.id}/status')
        assert response.status_code == 403

    def test_decorator_stacking(self, app, db_session, admin_user, member_user):
        """Test multiple decorators on same route."""
        from flask_login import login_required

        @app.route('/test-stacked')
        @login_required
        @require_company_admin
        def stacked_route():
            return 'stacked decorators'

        with app.test_client() as client:
            # Unauthenticated - should redirect
            response = client.get('/test-stacked')
            assert response.status_code in [302, 401]

            # Member - should be 403
            with client.session_transaction() as sess:
                sess['_user_id'] = str(member_user.id)
            response = client.get('/test-stacked')
            assert response.status_code == 403

            # Admin - should work
            with client.session_transaction() as sess:
                sess['_user_id'] = str(admin_user.id)
            response = client.get('/test-stacked')
            assert response.status_code != 403
