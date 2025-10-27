"""
Unit tests for database models.
"""
import pytest
from datetime import datetime
from app import create_app, db
from app.models import Company, User, Workspace


@pytest.fixture
def app():
    """Create application for testing."""
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
def sample_company(app):
    """Create sample company for testing."""
    company = Company(
        name='Test Company',
        subdomain='testco',
        plan='starter',
        max_workspaces=1
    )
    db.session.add(company)
    db.session.commit()
    return company


@pytest.fixture
def sample_user(app, sample_company):
    """Create sample user for testing."""
    user = User(
        email='test@example.com',
        username='testuser',
        full_name='Test User',
        role='admin',
        company_id=sample_company.id
    )
    user.set_password('testpassword123')
    db.session.add(user)
    db.session.commit()
    return user


class TestCompanyModel:
    """Tests for Company model."""

    def test_company_creation(self, app, sample_company):
        """Test company can be created."""
        assert sample_company.id is not None
        assert sample_company.name == 'Test Company'
        assert sample_company.subdomain == 'testco'
        assert sample_company.plan == 'starter'
        assert sample_company.status == 'active'
        assert sample_company.max_workspaces == 1

    def test_company_to_dict(self, app, sample_company):
        """Test company serialization."""
        data = sample_company.to_dict()
        assert data['name'] == 'Test Company'
        assert data['subdomain'] == 'testco'
        assert data['plan'] == 'starter'
        assert data['workspace_count'] == 0

    def test_can_create_workspace(self, app, sample_company):
        """Test workspace creation limit check."""
        assert sample_company.can_create_workspace() is True

        # Create workspace to reach limit
        workspace = Workspace(
            name='test-ws',
            subdomain='test-ws.testco',
            linux_username='testco_testws',
            port=8001,
            code_server_password='testpass',
            company_id=sample_company.id,
            owner_id=1
        )
        db.session.add(workspace)
        db.session.commit()

        assert sample_company.can_create_workspace() is False


class TestUserModel:
    """Tests for User model."""

    def test_user_creation(self, app, sample_user):
        """Test user can be created."""
        assert sample_user.id is not None
        assert sample_user.email == 'test@example.com'
        assert sample_user.username == 'testuser'
        assert sample_user.full_name == 'Test User'
        assert sample_user.role == 'admin'
        assert sample_user.is_active is True

    def test_password_hashing(self, app, sample_user):
        """Test password is properly hashed."""
        assert sample_user.password_hash != 'testpassword123'
        assert sample_user.check_password('testpassword123') is True
        assert sample_user.check_password('wrongpassword') is False

    def test_is_admin(self, app, sample_user):
        """Test admin role check."""
        assert sample_user.is_admin() is True

        sample_user.role = 'member'
        assert sample_user.is_admin() is False

    def test_user_to_dict(self, app, sample_user):
        """Test user serialization."""
        data = sample_user.to_dict()
        assert data['email'] == 'test@example.com'
        assert data['username'] == 'testuser'
        assert data['role'] == 'admin'
        assert 'password_hash' not in data


class TestWorkspaceModel:
    """Tests for Workspace model."""

    def test_workspace_creation(self, app, sample_company, sample_user):
        """Test workspace can be created."""
        workspace = Workspace(
            name='dev-workspace',
            subdomain='dev.testco',
            linux_username='testco_dev',
            port=8001,
            code_server_password='securepass123',
            disk_quota_gb=10,
            company_id=sample_company.id,
            owner_id=sample_user.id,
            status='pending'
        )
        db.session.add(workspace)
        db.session.commit()

        assert workspace.id is not None
        assert workspace.name == 'dev-workspace'
        assert workspace.port == 8001
        assert workspace.status == 'pending'

    def test_workspace_get_url(self, app, sample_company, sample_user):
        """Test workspace URL generation."""
        workspace = Workspace(
            name='dev-workspace',
            subdomain='dev.testco',
            linux_username='testco_dev',
            port=8001,
            code_server_password='securepass123',
            company_id=sample_company.id,
            owner_id=sample_user.id
        )
        db.session.add(workspace)
        db.session.commit()

        assert workspace.get_url() == 'https://dev.testco.youarecoder.com'

    def test_workspace_relationships(self, app, sample_company, sample_user):
        """Test workspace relationships with company and user."""
        workspace = Workspace(
            name='dev-workspace',
            subdomain='dev.testco',
            linux_username='testco_dev',
            port=8001,
            code_server_password='securepass123',
            company_id=sample_company.id,
            owner_id=sample_user.id
        )
        db.session.add(workspace)
        db.session.commit()

        assert workspace.company == sample_company
        assert workspace.owner == sample_user
        assert workspace in sample_company.workspaces
        assert workspace in sample_user.workspaces
