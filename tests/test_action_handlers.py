"""
Unit Tests for Action Handlers
Tests all 12 action handlers with mocking for external dependencies
"""
import pytest
import os
import tempfile
import subprocess
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime

from app.models import Workspace, WorkspaceTemplate
from app.services.action_handlers import (
    SSHKeyActionHandler,
    GitCloneActionHandler,
    SystemPackagesActionHandler,
    PythonVenvActionHandler,
    PipRequirementsActionHandler,
    DirectoryActionHandler,
    ConfigFileActionHandler,
    PostgreSQLDatabaseActionHandler,
    VSCodeExtensionsActionHandler,
    EnvironmentVariablesActionHandler,
    ShellScriptActionHandler,
    CompletionMessageActionHandler,
)


@pytest.fixture
def mock_workspace(db_session, company, admin_user):
    """Create mock workspace for handler testing"""
    workspace = Workspace(
        name='test-workspace',
        subdomain='testco-test',
        linux_username='testco_test',
        port=8001,
        code_server_password='test-password',
        status='provisioning',
        company_id=company.id,
        owner_id=admin_user.id
    )
    db_session.session.add(workspace)
    db_session.session.commit()
    return workspace


@pytest.fixture
def mock_template(db_session, company, admin_user):
    """Create mock template for handler testing"""
    template = WorkspaceTemplate(
        name='Test Template',
        description='Test template for handler testing',
        category='development',
        is_active=True,
        config={},
        created_by=admin_user.id,
        company_id=company.id
    )
    db_session.session.add(template)
    db_session.session.commit()
    return template


@pytest.fixture
def handler_context(mock_workspace):
    """
    Create handler initialization context from workspace.
    Returns dict that can be unpacked as **handler_context to initialize any handler.
    """
    return {
        'workspace_id': mock_workspace.id,
        'workspace_name': mock_workspace.name,
        'linux_username': mock_workspace.linux_username,
        'home_directory': f'/home/{mock_workspace.linux_username}',
        'subdomain': mock_workspace.subdomain
    }


# ==================== SSH Key Handler Tests ====================

class TestSSHKeyActionHandler:
    """Test SSH key generation handler"""

    def test_ssh_key_handler_initialization(self, handler_context):
        """Test handler initialization"""
        handler = SSHKeyActionHandler(**handler_context)
        assert handler.workspace_name == 'test-workspace'
        assert handler.linux_username == 'testco_test'
        assert handler.home_directory == '/home/testco_test'

    def test_validate_success(self, handler_context):
        """Test successful parameter validation"""
        handler = SSHKeyActionHandler(**handler_context)
        params = {
            'key_name': 'workspace_key',
            'key_type': 'ed25519'
        }
        assert handler.validate(params) is True

    def test_validate_invalid_key_type(self, handler_context):
        """Test validation with invalid key type"""
        handler = SSHKeyActionHandler(**handler_context)
        params = {
            'key_name': 'workspace_key',
            'key_type': 'invalid'
        }
        with pytest.raises(ValueError, match="Invalid key_type"):
            handler.validate(params)

    @patch('builtins.open', create=True)
    @patch('subprocess.run')
    @patch('os.chmod')
    @patch('os.makedirs')
    @patch('os.path.exists', return_value=False)
    def test_execute_success(self, mock_exists, mock_makedirs, mock_chmod, mock_run, mock_open, handler_context):
        """Test successful SSH key generation"""
        # Mock public key file read
        mock_open.return_value.__enter__.return_value.read.return_value = 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFoo workspace-1'

        handler = SSHKeyActionHandler(**handler_context)
        params = {
            'key_name': 'workspace_key',
            'key_type': 'ed25519',
            'passphrase': ''
        }

        mock_run.return_value = Mock(returncode=0)

        result = handler.execute(params)

        assert result['success'] is True
        assert 'private_key_path' in result
        assert 'public_key_path' in result
        assert 'public_key' in result
        mock_run.assert_called_once()

    @patch('builtins.open', create=True)
    @patch('subprocess.run')
    @patch('os.chmod')
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_execute_key_already_exists(self, mock_exists, mock_makedirs, mock_chmod, mock_run, mock_open, handler_context):
        """Test execution when key already exists"""
        # Mock: .ssh directory exists, key file exists
        mock_exists.side_effect = lambda path: True
        mock_run.return_value = Mock(returncode=0)
        # Mock public key file read
        mock_open.return_value.__enter__.return_value.read.return_value = 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFoo workspace-1'

        handler = SSHKeyActionHandler(**handler_context)
        params = {
            'key_name': 'workspace_key',
            'key_type': 'ed25519'
        }

        result = handler.execute(params)

        assert result['success'] is True
        assert result['already_existed'] is True


# ==================== Git Clone Handler Tests ====================

class TestGitCloneActionHandler:
    """Test Git repository cloning handler"""

    def test_validate_success(self, handler_context):
        """Test successful parameter validation"""
        handler = GitCloneActionHandler(**handler_context)
        params = {
            'repo_url': 'https://github.com/user/repo.git',
            'destination_path': '/home/testco_test/project'
        }
        assert handler.validate(params) is True

    def test_validate_missing_required(self, handler_context):
        """Test validation with missing required parameter"""
        handler = GitCloneActionHandler(**handler_context)
        params = {
            'destination_path': '/home/testco_test/project'
        }
        with pytest.raises(ValueError, match="Missing required parameter"):
            handler.validate(params)

    @patch('subprocess.run')
    @patch('os.path.exists', return_value=False)
    def test_execute_success(self, mock_exists, mock_run, handler_context):
        """Test successful git clone"""
        handler = GitCloneActionHandler(**handler_context)
        params = {
            'repo_url': 'https://github.com/user/repo.git',
            'destination_path': '/home/testco_test/project'
        }

        # Mock git clone and subsequent git commands
        mock_run.side_effect = [
            Mock(returncode=0, stdout='', stderr=''),  # git clone
            Mock(returncode=0, stdout='abc123def456', stderr=''),  # git rev-parse HEAD
            Mock(returncode=0, stdout='main', stderr=''),  # git rev-parse --abbrev-ref HEAD
        ]

        result = handler.execute(params)

        assert result['success'] is True
        assert result['repo_url'] == params['repo_url']
        assert result['repo_path'] == params['destination_path']
        assert result['commit_hash'] == 'abc123def456'
        assert result['branch'] == 'main'
        assert mock_run.call_count == 3


# ==================== System Packages Handler Tests ====================

class TestSystemPackagesActionHandler:
    """Test system package installation handler"""

    def test_validate_success(self, handler_context):
        """Test successful parameter validation"""
        handler = SystemPackagesActionHandler(**handler_context)
        params = {
            'packages': ['git', 'python3', 'postgresql']
        }
        assert handler.validate(params) is True

    def test_validate_empty_packages(self, handler_context):
        """Test validation with empty package list"""
        handler = SystemPackagesActionHandler(**handler_context)
        params = {'packages': []}
        with pytest.raises(ValueError, match="Packages list cannot be empty"):
            handler.validate(params)

    @patch('subprocess.run')
    def test_execute_success(self, mock_run, handler_context):
        """Test successful package installation"""
        handler = SystemPackagesActionHandler(**handler_context)
        params = {
            'packages': ['git', 'python3'],
            'update_cache': True
        }

        mock_run.return_value = Mock(returncode=0)

        result = handler.execute(params)

        assert result['success'] is True
        assert len(result['installed_packages']) == 2
        assert mock_run.call_count >= 3  # update + 2 packages


# ==================== Python Venv Handler Tests ====================

class TestPythonVenvActionHandler:
    """Test Python virtual environment creation handler"""

    def test_validate_success(self, handler_context):
        """Test successful parameter validation"""
        handler = PythonVenvActionHandler(**handler_context)
        params = {
            'venv_path': '/home/testco_test/venv'
        }
        assert handler.validate(params) is True

    @patch('subprocess.run')
    @patch('os.path.exists', return_value=False)
    def test_execute_success(self, mock_exists, mock_run, handler_context):
        """Test successful venv creation"""
        handler = PythonVenvActionHandler(**handler_context)
        params = {
            'venv_path': '/home/testco_test/venv',
            'python_version': 'python3'
        }

        mock_run.return_value = Mock(returncode=0)

        result = handler.execute(params)

        assert result['success'] is True
        assert result['venv_path'] == params['venv_path']
        assert 'activate_script' in result


# ==================== Pip Requirements Handler Tests ====================

class TestPipRequirementsActionHandler:
    """Test pip package installation handler"""

    def test_validate_at_least_one_source(self, handler_context):
        """Test validation requires at least one package source"""
        handler = PipRequirementsActionHandler(**handler_context)
        params = {}
        with pytest.raises(ValueError, match="Either requirements_file or packages must be specified"):
            handler.validate(params)

    @patch('subprocess.run')
    @patch('os.path.exists', return_value=True)
    def test_execute_with_requirements_file(self, mock_exists, mock_run, handler_context):
        """Test installation from requirements.txt"""
        handler = PipRequirementsActionHandler(**handler_context)
        params = {
            'requirements_file': '/home/testco_test/requirements.txt',
            'venv_path': '/home/testco_test/venv'
        }

        mock_run.return_value = Mock(returncode=0)

        result = handler.execute(params)

        assert result['success'] is True
        assert len(result['installed_items']) == 1


# ==================== Directory Handler Tests ====================

class TestDirectoryActionHandler:
    """Test directory creation handler"""

    def test_validate_success(self, handler_context):
        """Test successful parameter validation"""
        handler = DirectoryActionHandler(**handler_context)
        params = {
            'path': '/home/testco_test/project'
        }
        assert handler.validate(params) is True

    @patch('os.makedirs')
    @patch('os.path.exists', return_value=True)
    @patch('os.path.isdir', return_value=True)
    def test_execute_success(self, mock_isdir, mock_exists, mock_makedirs, handler_context):
        """Test successful directory creation"""
        handler = DirectoryActionHandler(**handler_context)
        params = {
            'path': '/home/testco_test/project',
            'mode': 0o755,
            'parents': True
        }

        result = handler.execute(params)

        assert result['success'] is True
        assert result['path'] == params['path']
        mock_makedirs.assert_called_once()


# ==================== Config File Handler Tests ====================

class TestConfigFileActionHandler:
    """Test configuration file writing handler"""

    def test_validate_success(self, handler_context):
        """Test successful parameter validation"""
        handler = ConfigFileActionHandler(**handler_context)
        params = {
            'file_path': '/home/testco_test/config.ini',
            'content': '[section]\nkey=value'
        }
        assert handler.validate(params) is True

    @patch('builtins.open', create=True)
    @patch('os.makedirs')
    @patch('os.path.exists', return_value=False)
    @patch('os.chmod')
    @patch('os.path.getsize', return_value=100)
    def test_execute_text_format(self, mock_getsize, mock_chmod, mock_exists, mock_makedirs, mock_open, handler_context):
        """Test writing text configuration file"""
        handler = ConfigFileActionHandler(**handler_context)
        params = {
            'file_path': '/home/testco_test/config.ini',
            'content': '[section]\nkey=value',
            'format': 'text',
            'mode': 0o644
        }

        result = handler.execute(params)

        assert result['success'] is True
        assert result['format'] == 'text'


# ==================== PostgreSQL Handler Tests ====================

class TestPostgreSQLDatabaseActionHandler:
    """Test PostgreSQL database creation handler"""

    @patch('subprocess.run')
    def test_validate_success(self, mock_run, handler_context):
        """Test successful parameter validation"""
        # Mock psql --version check
        mock_run.return_value = Mock(returncode=0, stdout='psql (PostgreSQL) 14.0', stderr='')

        handler = PostgreSQLDatabaseActionHandler(**handler_context)
        params = {
            'database_name': 'testdb'
        }
        assert handler.validate(params) is True

    def test_validate_invalid_db_name(self, handler_context):
        """Test validation with invalid database name"""
        handler = PostgreSQLDatabaseActionHandler(**handler_context)
        params = {
            'database_name': 'test db'  # Space not allowed
        }
        with pytest.raises(ValueError, match="Invalid database name"):
            handler.validate(params)

    @patch('subprocess.run')
    def test_execute_success(self, mock_run, handler_context):
        """Test successful database creation"""
        handler = PostgreSQLDatabaseActionHandler(**handler_context)
        params = {
            'database_name': 'testdb',
            'username': 'testuser'
        }

        # Mock user doesn't exist
        mock_run.side_effect = [
            Mock(returncode=0, stdout=''),  # Check user (not exists)
            Mock(returncode=0),  # Create user
            Mock(returncode=0, stdout=''),  # Check DB (not exists)
            Mock(returncode=0),  # Create DB
            Mock(returncode=0),  # Grant privileges
        ]

        result = handler.execute(params)

        assert result['success'] is True
        assert result['database_name'] == 'testdb'
        assert result['user_created'] is True


# ==================== VS Code Extensions Handler Tests ====================

class TestVSCodeExtensionsActionHandler:
    """Test VS Code extension installation handler"""

    def test_validate_success(self, handler_context):
        """Test successful parameter validation"""
        handler = VSCodeExtensionsActionHandler(**handler_context)
        params = {
            'extensions': ['ms-python.python', 'dbaeumer.vscode-eslint']
        }

        with patch('subprocess.run', return_value=Mock(returncode=0)):
            assert handler.validate(params) is True

    @patch('subprocess.run')
    def test_execute_success(self, mock_run, handler_context):
        """Test successful extension installation"""
        handler = VSCodeExtensionsActionHandler(**handler_context)
        params = {
            'extensions': ['ms-python.python']
        }

        mock_run.return_value = Mock(returncode=0)

        result = handler.execute(params)

        assert result['success'] is True
        assert len(result['installed_extensions']) == 1
        assert result['failed_extensions'] == []


# ==================== Environment Variables Handler Tests ====================

class TestEnvironmentVariablesActionHandler:
    """Test environment variables setting handler"""

    def test_validate_success(self, handler_context):
        """Test successful parameter validation"""
        handler = EnvironmentVariablesActionHandler(**handler_context)
        params = {
            'variables': {
                'PATH': '/usr/local/bin:$PATH',
                'PYTHONPATH': '/home/testco_test/lib'
            }
        }
        assert handler.validate(params) is True

    def test_validate_invalid_var_name(self, handler_context):
        """Test validation with invalid variable name"""
        handler = EnvironmentVariablesActionHandler(**handler_context)
        params = {
            'variables': {
                'INVALID-NAME': 'value'  # Hyphen not allowed
            }
        }
        with pytest.raises(ValueError, match="Invalid variable name"):
            handler.validate(params)

    @patch('builtins.open', create=True)
    @patch('os.path.exists', return_value=False)
    @patch('os.makedirs')
    def test_execute_success(self, mock_makedirs, mock_exists, mock_open, handler_context):
        """Test successful environment variable setting"""
        handler = EnvironmentVariablesActionHandler(**handler_context)
        params = {
            'variables': {
                'PATH': '/usr/local/bin:$PATH'
            },
            'shell_config_file': '/home/testco_test/.bashrc'
        }

        result = handler.execute(params)

        assert result['success'] is True
        assert len(result['variables_set']) == 1


# ==================== Shell Script Handler Tests ====================

class TestShellScriptActionHandler:
    """Test shell script execution handler"""

    def test_validate_requires_one_method(self, handler_context):
        """Test validation requires one execution method"""
        handler = ShellScriptActionHandler(**handler_context)
        params = {}
        with pytest.raises(ValueError, match="Must specify one of"):
            handler.validate(params)

    @patch('subprocess.run')
    def test_execute_command(self, mock_run, handler_context):
        """Test successful command execution"""
        handler = ShellScriptActionHandler(**handler_context)
        params = {
            'command': 'echo "Hello World"',
            'timeout': 60
        }

        mock_run.return_value = Mock(
            returncode=0,
            stdout='Hello World\n',
            stderr=''
        )

        result = handler.execute(params)

        assert result['success'] is True
        assert result['exit_code'] == 0
        assert 'Hello World' in result['stdout']

    @patch('subprocess.run')
    def test_execute_timeout(self, mock_run, handler_context):
        """Test script timeout handling"""
        handler = ShellScriptActionHandler(**handler_context)
        params = {
            'command': 'sleep 100',
            'timeout': 1
        }

        mock_run.side_effect = subprocess.TimeoutExpired('sleep', 1)

        with pytest.raises(Exception, match="timed out"):
            handler.execute(params)


# ==================== Completion Message Handler Tests ====================

class TestCompletionMessageActionHandler:
    """Test completion message display handler"""

    def test_validate_always_true(self, handler_context):
        """Test validation always succeeds"""
        handler = CompletionMessageActionHandler(**handler_context)
        assert handler.validate({}) is True

    def test_execute_default_message(self, handler_context):
        """Test default completion message"""
        handler = CompletionMessageActionHandler(**handler_context)
        params = {}

        result = handler.execute(params)

        assert result['success'] is True
        assert 'completed successfully' in result['message']
        assert result['workspace_name'] == 'test-workspace'

    def test_execute_custom_message(self, handler_context):
        """Test custom completion message"""
        handler = CompletionMessageActionHandler(**handler_context)
        params = {
            'message': 'Custom success message',
            'include_credentials': False,
            'include_urls': False
        }

        result = handler.execute(params)

        assert result['success'] is True
        assert 'Custom success message' in result['message']


# ==================== Variable Substitution Tests ====================

class TestVariableSubstitution:
    """Test variable substitution in handlers"""

    def test_substitute_workspace_variables(self, handler_context):
        """Test substitution of workspace variables"""
        handler = SSHKeyActionHandler(**handler_context)
        params = {
            'key_name': '{workspace_name}_key',
            'output_path': '{home_directory}/.ssh'
        }

        result = handler.substitute_variables(params)

        assert result['key_name'] == 'test-workspace_key'
        assert result['output_path'] == '/home/testco_test/.ssh'

    def test_substitute_nested_dict(self, handler_context):
        """Test substitution in nested dictionary"""
        handler = ConfigFileActionHandler(**handler_context)
        params = {
            'file_path': '{home_directory}/config.ini',
            'content': {
                'user': '{workspace_linux_username}',
                'workspace': '{workspace_name}'
            }
        }

        result = handler.substitute_variables(params)

        assert result['content']['user'] == 'testco_test'
        assert result['content']['workspace'] == 'test-workspace'


# ==================== Rollback Tests ====================

class TestHandlerRollback:
    """Test rollback functionality"""

    @patch('os.path.exists', return_value=True)
    @patch('os.remove')
    def test_ssh_key_rollback(self, mock_remove, mock_exists, handler_context):
        """Test SSH key handler rollback"""
        handler = SSHKeyActionHandler(**handler_context)
        execution_result = {
            'success': True,
            'private_key_path': '/home/testco_test/.ssh/key',
            'public_key_path': '/home/testco_test/.ssh/key.pub',
            'key_created': True
        }

        result = handler.rollback({}, execution_result)

        assert result is True
        assert mock_remove.call_count == 2

    @patch('subprocess.run')
    def test_postgres_rollback(self, mock_run, handler_context):
        """Test PostgreSQL handler rollback"""
        handler = PostgreSQLDatabaseActionHandler(**handler_context)
        execution_result = {
            'success': True,
            'database_name': 'testdb',
            'username': 'testuser',
            'database_created': True,
            'user_created': True
        }

        mock_run.return_value = Mock(returncode=0)

        result = handler.rollback({}, execution_result)

        assert result is True
        assert mock_run.call_count >= 2  # Drop DB + Drop User


# ==================== Integration Tests ====================

class TestHandlerIntegration:
    """Test handlers working together"""

    @patch('subprocess.run')
    @patch('os.makedirs')
    @patch('os.path.exists', return_value=False)
    def test_full_workspace_setup_flow(self, mock_exists, mock_makedirs, mock_run,
                                      handler_context):
        """Test realistic workspace setup flow"""
        mock_run.return_value = Mock(returncode=0, stdout='', stderr='')

        # 1. Create directory
        dir_handler = DirectoryActionHandler(**handler_context)
        dir_result = dir_handler.execute({
            'path': '/home/testco_test/project'
        })
        assert dir_result['success'] is True

        # 2. Install packages
        pkg_handler = SystemPackagesActionHandler(**handler_context)
        pkg_result = pkg_handler.execute({
            'packages': ['python3', 'git']
        })
        assert pkg_result['success'] is True

        # 3. Create venv
        venv_handler = PythonVenvActionHandler(**handler_context)
        venv_result = venv_handler.execute({
            'venv_path': '/home/testco_test/venv'
        })
        assert venv_result['success'] is True

        # 4. Display completion
        completion_handler = CompletionMessageActionHandler(**handler_context)
        completion_result = completion_handler.execute({})
        assert completion_result['success'] is True
