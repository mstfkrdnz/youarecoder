"""
Pytest configuration and fixtures for YouAreCoder test suite.
"""
import pytest
from datetime import datetime, timedelta
from app import create_app, db
from app.models import User, Company, Workspace, LoginAttempt


@pytest.fixture(scope='session')
def app():
    """Create Flask application for testing."""
    app = create_app('test')

    # Override configuration for testing
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,  # Disable CSRF for testing
        'RATELIMIT_ENABLED': False,  # Disable rate limiting for most tests
        'SECRET_KEY': 'test-secret-key',
    })

    # Register test routes for decorator testing BEFORE any requests
    with app.app_context():
        from flask_login import login_required
        from app.utils.decorators import require_role, require_company_admin

        @app.route('/test-admin-only')
        @login_required
        @require_role('admin')
        def test_admin_only():
            return 'admin access'

        @app.route('/test-multi-role')
        @login_required
        @require_role('admin', 'member')
        def test_multi_role():
            return 'multi role access'

        @app.route('/test-company-admin')
        @login_required
        @require_company_admin
        def test_company_admin():
            return 'company admin access'

        @app.route('/test-company-admin-forbidden')
        @login_required
        @require_company_admin
        def test_company_admin_forbidden():
            return 'company admin forbidden test'

        @app.route('/test-decorator-stack')
        @login_required
        @require_role('admin')
        @require_company_admin
        def test_decorator_stack():
            return 'stacked decorators'

    return app


@pytest.fixture(scope='function')
def client(app):
    """Create Flask test client."""
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    """Create Flask CLI test runner."""
    return app.test_cli_runner()


@pytest.fixture(scope='function')
def db_session(app):
    """Create database session for testing."""
    with app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()


@pytest.fixture
def company(db_session):
    """Create test company."""
    company = Company(
        name='Test Company',
        subdomain='testco',
        plan='starter',
        max_workspaces=1
    )
    db_session.session.add(company)
    db_session.session.commit()
    return company


@pytest.fixture
def admin_user(db_session, company):
    """Create test admin user."""
    user = User(
        email='admin@test.com',
        full_name='Admin User',
        role='admin',
        company_id=company.id
    )
    user.set_password('AdminPass123!')
    db_session.session.add(user)
    db_session.session.commit()
    return user


@pytest.fixture
def member_user(db_session, company):
    """Create test member user."""
    user = User(
        email='member@test.com',
        full_name='Member User',
        role='member',
        company_id=company.id
    )
    user.set_password('MemberPass123!')
    db_session.session.add(user)
    db_session.session.commit()
    return user


@pytest.fixture
def other_company(db_session):
    """Create another test company for isolation testing."""
    company = Company(
        name='Other Company',
        subdomain='otherco',
        plan='team',
        max_workspaces=5
    )
    db_session.session.add(company)
    db_session.session.commit()
    return company


@pytest.fixture
def other_user(db_session, other_company):
    """Create user from different company."""
    user = User(
        email='other@test.com',
        username='other',
        full_name='Other User',
        role='admin',
        company_id=other_company.id
    )
    user.set_password('OtherPass123!')
    db_session.session.add(user)
    db_session.session.commit()
    return user


@pytest.fixture
def workspace(db_session, company, admin_user):
    """Create test workspace."""
    workspace = Workspace(
        name='test-workspace',
        subdomain='testco-test',
        linux_username='testco_test',
        port=8001,
        code_server_password='test-password',
        status='active',
        company_id=company.id,
        owner_id=admin_user.id
    )
    db_session.session.add(workspace)
    db_session.session.commit()
    return workspace


@pytest.fixture
def other_workspace(db_session, other_company, other_user):
    """Create workspace for other company."""
    workspace = Workspace(
        name='other-workspace',
        subdomain='otherco-other',
        linux_username='otherco_other',
        port=8002,
        code_server_password='other-password',
        status='active',
        company_id=other_company.id,
        owner_id=other_user.id
    )
    db_session.session.add(workspace)
    db_session.session.commit()
    return workspace


@pytest.fixture
def authenticated_client(client, db_session, admin_user):
    """Create authenticated test client."""
    with client:
        # Properly login using Flask-Login
        from flask_login import login_user
        with client.application.test_request_context():
            login_user(admin_user)

        # Also use session transaction for additional persistence
        with client.session_transaction() as sess:
            sess['_user_id'] = str(admin_user.id)
            sess['_fresh'] = True

        yield client


def login_as_user(client, user):
    """Helper function to login as specific user in tests."""
    from flask_login import login_user
    with client.application.test_request_context():
        login_user(user)

    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)
        sess['_fresh'] = True

    return client


@pytest.fixture
def app_with_rate_limiting(app):
    """Flask app with rate limiting enabled."""
    app.config['RATELIMIT_ENABLED'] = True
    return app


@pytest.fixture
def production_app():
    """Flask app in production mode for security headers testing."""
    # Create app with test config first to avoid PostgreSQL connection
    app = create_app('test')

    # Then manually initialize Talisman for production-like security headers
    from flask_talisman import Talisman
    Talisman(app,
        force_https=False,  # Don't force HTTPS in tests
        strict_transport_security=True,
        strict_transport_security_max_age=31536000,
        strict_transport_security_include_subdomains=True,
        content_security_policy={
            'default-src': ["'self'"],
            'script-src': ["'self'", 'https://cdn.tailwindcss.com', 'https://unpkg.com', "'unsafe-inline'"],
            'style-src': ["'self'", 'https://cdn.tailwindcss.com', "'unsafe-inline'"],
            'img-src': ["'self'", 'data:', 'https:'],
            'font-src': ["'self'", 'https:', 'data:'],
            'connect-src': ["'self'"],
            'frame-ancestors': ["'none'"],
        },
        feature_policy={
            'geolocation': "'none'",
            'microphone': "'none'",
            'camera': "'none'",
        },
        referrer_policy='strict-origin-when-cross-origin',
        force_file_save=False
    )

    return app
