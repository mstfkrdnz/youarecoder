"""
Unit tests for WorkspaceProvisioner service.
"""
import pytest
from app import create_app, db
from app.models import Company, User, Workspace
from app.services.workspace_provisioner import (
    WorkspaceProvisioner,
    PortAllocationError
)


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
def provisioner(app):
    """Create provisioner instance."""
    return WorkspaceProvisioner()


class TestPortAllocation:
    """Tests for port allocation."""

    def test_allocate_first_port(self, app, provisioner):
        """Test allocating first port in range."""
        port = provisioner.allocate_port()
        assert port == app.config['WORKSPACE_PORT_RANGE_START']

    def test_allocate_next_available_port(self, app, provisioner):
        """Test allocating next available port when some are used."""
        # Create workspace with first port
        company = Company(name='Test', subdomain='test', plan='starter', max_workspaces=5)
        db.session.add(company)
        db.session.flush()

        workspace = Workspace(
            name='ws1',
            subdomain='ws1.test',
            linux_username='test_ws1',
            port=8001,
            code_server_password='pass',
            company_id=company.id,
            owner_id=1
        )
        db.session.add(workspace)
        db.session.commit()

        # Next port should be 8002
        port = provisioner.allocate_port()
        assert port == 8002

    def test_port_allocation_error_when_full(self, app, provisioner):
        """Test error when all ports are allocated."""
        company = Company(name='Test', subdomain='test', plan='starter', max_workspaces=200)
        db.session.add(company)
        db.session.flush()

        # Fill all ports
        for port in range(app.config['WORKSPACE_PORT_RANGE_START'],
                         app.config['WORKSPACE_PORT_RANGE_END'] + 1):
            workspace = Workspace(
                name=f'ws{port}',
                subdomain=f'ws{port}.test',
                linux_username=f'test_ws{port}',
                port=port,
                code_server_password='pass',
                company_id=company.id,
                owner_id=1
            )
            db.session.add(workspace)
        db.session.commit()

        # Should raise error
        with pytest.raises(PortAllocationError):
            provisioner.allocate_port()


class TestPasswordGeneration:
    """Tests for password generation."""

    def test_generate_password_default_length(self, app, provisioner):
        """Test password generation with default length."""
        password = provisioner.generate_password()
        assert len(password) == 18
        assert password.isalnum()

    def test_generate_password_custom_length(self, app, provisioner):
        """Test password generation with custom length."""
        password = provisioner.generate_password(24)
        assert len(password) == 24
        assert password.isalnum()

    def test_generate_password_uniqueness(self, app, provisioner):
        """Test that generated passwords are unique."""
        passwords = [provisioner.generate_password() for _ in range(100)]
        assert len(set(passwords)) == 100  # All unique
