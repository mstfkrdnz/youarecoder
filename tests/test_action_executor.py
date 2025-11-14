"""
Integration Tests for ActionExecutor
Tests the orchestration engine and DAG resolution
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from app.models import (
    Workspace, WorkspaceTemplate, TemplateActionSequence,
    WorkspaceActionExecution
)
from app.services.action_executor import ActionExecutor
from app.services.action_handlers import SSHKeyActionHandler, GitCloneActionHandler


@pytest.fixture
def action_template(db_session, company, admin_user):
    """Create template with action sequences"""
    template = WorkspaceTemplate(
        name='Test Action Template',
        description='Template with action sequences',
        category='development',
        config={},
        created_by=admin_user.id,
        company_id=company.id,
        is_active=True,
        rollback_on_fatal_error=True  # Enable rollback for testing
    )
    db_session.session.add(template)
    db_session.session.commit()

    # Add action sequences
    actions = [
        TemplateActionSequence(
            template_id=template.id,
            action_id='ssh-key-gen',
            action_type='generate_ssh_key',
            display_name='Generate SSH Key',
            description='Generate SSH key pair for workspace',
            category='security',
            parameters={
                'key_name': 'workspace_key',
                'key_type': 'ed25519'
            },
            order=1,
            enabled=True
        ),
        TemplateActionSequence(
            template_id=template.id,
            action_id='git-clone-repo',
            action_type='clone_git_repository',
            display_name='Clone Repository',
            description='Clone project repository',
            category='development',
            parameters={
                'repo_url': 'https://github.com/test/repo.git',
                'destination_path': '{home_directory}/project'
            },
            order=2,
            enabled=True,
            fatal_on_error=True,  # Git failures should stop execution
            dependencies=['ssh-key-gen']  # Depends on SSH key
        ),
        TemplateActionSequence(
            template_id=template.id,
            action_id='completion-msg',
            action_type='display_completion_message',
            display_name='Completion Message',
            description='Display setup completion message',
            category='notification',
            parameters={
                'message': 'Setup complete!'
            },
            order=3,
            enabled=True,
            fatal_on_error=True,  # Completion message failures should trigger rollback
            dependencies=['git-clone-repo']  # Depends on git clone
        )
    ]

    for action in actions:
        db_session.session.add(action)
    db_session.session.commit()

    return template


@pytest.fixture
def test_workspace(db_session, company, admin_user):
    """Create test workspace"""
    workspace = Workspace(
        name='executor-test',
        subdomain='testco-exec',
        linux_username='testco_exec',
        port=8003,
        code_server_password='test-pass',
        status='provisioning',
        company_id=company.id,
        owner_id=admin_user.id
    )
    db_session.session.add(workspace)
    db_session.session.commit()
    return workspace


class TestActionExecutorInitialization:
    """Test ActionExecutor initialization"""

    def test_executor_initialization(self, test_workspace, action_template):
        """Test executor initializes correctly"""
        executor = ActionExecutor(test_workspace, action_template)

        assert executor.workspace == test_workspace
        assert executor.template == action_template
        assert executor.completed_actions == []
        assert executor.failed_action is None

    def test_handler_registry_populated(self, test_workspace, action_template):
        """Test handler registry contains all handlers"""
        executor = ActionExecutor(test_workspace, action_template)

        expected_handlers = [
            'generate_ssh_key',
            'clone_git_repository',
            'install_system_packages',
            'create_python_venv',
            'install_pip_requirements',
            'create_directory',
            'write_configuration_file',
            'create_postgresql_database',
            'install_vscode_extensions',
            'set_environment_variables',
            'execute_shell_script',
            'display_completion_message',
        ]

        for handler_type in expected_handlers:
            assert handler_type in executor.HANDLER_REGISTRY


class TestActionExecutorDAG:
    """Test DAG dependency resolution"""

    def test_build_dag_simple(self, test_workspace, db_session, company, admin_user):
        """Test DAG building with simple dependencies"""
        template = WorkspaceTemplate(
            name='Simple DAG Template',
            category='development',
            config={},
            created_by=admin_user.id,
            company_id=company.id,
            is_active=True
        )
        db_session.session.add(template)
        db_session.session.commit()

        # Create linear dependency chain: A -> B -> C
        actions = [
            TemplateActionSequence(
                template_id=template.id,
                action_id='create-dir-1',
                action_type='create_directory',
                display_name='Create Directory',
                category='infrastructure',
                parameters={'path': '/tmp/test'},
                order=1,
                enabled=True
            ),
            TemplateActionSequence(
                template_id=template.id,
                action_id='create-dir-2',
                action_type='create_directory',
                display_name='Create Subdirectory',
                category='infrastructure',
                parameters={'path': '/tmp/test/sub'},
                order=2,
                enabled=True,
                dependencies=[1]
            ),
            TemplateActionSequence(
                template_id=template.id,
                action_id='completion-1',
                action_type='display_completion_message',
                display_name='Completion Message',
                category='notification',
                parameters={},
                order=3,
                enabled=True,
                dependencies=[2]
            )
        ]

        for action in actions:
            db_session.session.add(action)
        db_session.session.commit()

        executor = ActionExecutor(test_workspace, template)
        sorted_actions = executor._resolve_dependencies(actions)

        # Verify order: A -> B -> C (linear dependency)
        assert len(sorted_actions) == 3
        assert sorted_actions[0].action_id == 'create-dir-1'
        assert sorted_actions[1].action_id == 'create-dir-2'
        assert sorted_actions[2].action_id == 'completion-1'

    def test_build_dag_parallel(self, test_workspace, db_session, company, admin_user):
        """Test DAG building with parallel actions"""
        template = WorkspaceTemplate(
            name='Parallel DAG Template',
            category='development',
            config={},
            created_by=admin_user.id,
            company_id=company.id,
            is_active=True
        )
        db_session.session.add(template)
        db_session.session.commit()

        # Create parallel structure:
        #     A
        #    / \
        #   B   C
        #    \ /
        #     D
        actions = [
            TemplateActionSequence(
                template_id=template.id,
                action_id='root-dir',
                action_type='create_directory',
                display_name='Create Root Directory',
                category='infrastructure',
                parameters={'path': '/tmp/root'},
                order=1,
                enabled=True
            ),
            TemplateActionSequence(
                template_id=template.id,
                action_id='branch-1',
                action_type='create_directory',
                display_name='Create Branch 1',
                category='infrastructure',
                parameters={'path': '/tmp/root/branch1'},
                order=2,
                enabled=True,
                dependencies=[1]
            ),
            TemplateActionSequence(
                template_id=template.id,
                action_id='branch-2',
                action_type='create_directory',
                display_name='Create Branch 2',
                category='infrastructure',
                parameters={'path': '/tmp/root/branch2'},
                order=3,
                enabled=True,
                dependencies=[1]
            ),
            TemplateActionSequence(
                template_id=template.id,
                action_id='merge-completion',
                action_type='display_completion_message',
                display_name='Completion Message',
                category='notification',
                parameters={},
                order=4,
                enabled=True,
                dependencies=[2, 3]  # Depends on both branches
            )
        ]

        for action in actions:
            db_session.session.add(action)
        db_session.session.commit()

        executor = ActionExecutor(test_workspace, template)
        sorted_actions = executor._resolve_dependencies(actions)

        # Verify: root-dir comes first, then branch-1 and branch-2 (in any order),
        # then merge-completion comes last
        assert len(sorted_actions) == 4
        assert sorted_actions[0].action_id == 'root-dir'
        assert sorted_actions[3].action_id == 'merge-completion'
        # Middle two can be in any order
        middle_ids = {sorted_actions[1].action_id, sorted_actions[2].action_id}
        assert middle_ids == {'branch-1', 'branch-2'}

    def test_topological_sort_simple(self, test_workspace, action_template):
        """Test topological sort produces correct order"""
        executor = ActionExecutor(test_workspace, action_template)

        action_sequences = TemplateActionSequence.query.filter_by(
            template_id=action_template.id,
            enabled=True
        ).order_by(TemplateActionSequence.order).all()

        sorted_actions = executor._resolve_dependencies(action_sequences)

        # Verify order: SSH key -> Git clone -> Completion
        assert sorted_actions[0].action_type == 'generate_ssh_key'
        assert sorted_actions[1].action_type == 'clone_git_repository'
        assert sorted_actions[2].action_type == 'display_completion_message'

    def test_detect_circular_dependency(self, test_workspace, db_session, company, admin_user):
        """Test circular dependency detection"""
        template = WorkspaceTemplate(
            name='Circular Template',
            category='development',
            config={},
            created_by=admin_user.id,
            company_id=company.id,
            is_active=True
        )
        db_session.session.add(template)
        db_session.session.commit()

        # Create circular dependency: A -> B -> A
        action_a = TemplateActionSequence(
            template_id=template.id,
            action_id='circular-a',
            action_type='create_directory',
            display_name='Directory A',
            category='infrastructure',
            parameters={'path': '/tmp/a'},
            order=1,
            enabled=True,
            dependencies=['circular-b']  # Circular: A depends on B
        )
        action_b = TemplateActionSequence(
            template_id=template.id,
            action_id='circular-b',
            action_type='create_directory',
            display_name='Directory B',
            category='infrastructure',
            parameters={'path': '/tmp/b'},
            order=2,
            enabled=True,
            dependencies=['circular-a']  # Circular: B depends on A
        )

        db_session.session.add_all([action_a, action_b])
        db_session.session.commit()

        executor = ActionExecutor(test_workspace, template)

        with pytest.raises(ValueError, match="Circular dependency"):
            executor._resolve_dependencies([action_a, action_b])


class TestActionExecutorExecution:
    """Test action execution flow"""

    @patch('app.services.action_handlers.SSHKeyActionHandler.execute')
    @patch('app.services.action_handlers.GitCloneActionHandler.execute')
    @patch('app.services.action_handlers.CompletionMessageActionHandler.execute')
    def test_execute_template_actions_success(self, mock_completion, mock_git, mock_ssh,
                                             test_workspace, action_template, db_session):
        """Test successful execution of all template actions"""
        # Mock successful execution
        mock_ssh.return_value = {
            'success': True,
            'private_key_path': '/home/testco_exec/.ssh/key',
            'public_key_path': '/home/testco_exec/.ssh/key.pub'
        }
        mock_git.return_value = {
            'success': True,
            'repository_url': 'https://github.com/test/repo.git'
        }
        mock_completion.return_value = {
            'success': True,
            'message': 'Setup complete!'
        }

        executor = ActionExecutor(test_workspace, action_template)
        result = executor.execute_template_actions()

        assert result['success'] is True
        assert len(result['completed_actions']) == 3
        assert result.get('failed_action') is None

        # Verify execution records created
        executions = WorkspaceActionExecution.query.filter_by(
            workspace_id=test_workspace.id
        ).all()
        assert len(executions) == 3

    @patch('app.services.action_handlers.CompletionMessageActionHandler.execute')
    @patch('app.services.action_handlers.GitCloneActionHandler.execute')
    @patch('app.services.action_handlers.SSHKeyActionHandler.execute')
    def test_execute_template_actions_failure(self, mock_ssh, mock_git, mock_completion,
                                             test_workspace, action_template, db_session):
        """Test execution stops on first failure"""
        # Mock SSH success, Git failure, Completion should not be called
        mock_ssh.return_value = {
            'success': True,
            'private_key_path': '/home/testco_exec/.ssh/key'
        }
        mock_git.side_effect = Exception("Git clone failed")
        mock_completion.return_value = {'success': True}  # Should not be reached

        executor = ActionExecutor(test_workspace, action_template)
        result = executor.execute_template_actions()

        assert result['success'] is False
        assert len(result['completed_actions']) == 1  # Only SSH key
        assert result.get('failed_action') == 'git-clone-repo'
        assert 'Fatal error in action git-clone-repo' in result['error']

        # Verify completion was not called
        mock_completion.assert_not_called()

    @patch('app.services.action_handlers.SSHKeyActionHandler.execute')
    def test_execute_single_action_success(self, mock_execute, test_workspace, action_template):
        """Test successful single action execution"""
        mock_execute.return_value = {
            'success': True,
            'private_key_path': '/home/testco_exec/.ssh/key'
        }

        action_sequence = TemplateActionSequence.query.filter_by(
            template_id=action_template.id,
            action_type='generate_ssh_key'
        ).first()

        executor = ActionExecutor(test_workspace, action_template)
        execution = executor._execute_single_action(action_sequence)

        assert execution.status == 'completed'
        assert execution.error_message is None
        assert 'private_key_path' in execution.result

    @patch('app.services.action_handlers.SSHKeyActionHandler.validate')
    @patch('app.services.action_handlers.SSHKeyActionHandler.execute')
    def test_execute_single_action_with_retry(self, mock_execute, mock_validate, test_workspace, db_session, company, admin_user):
        """Test action retry on failure"""
        template = WorkspaceTemplate(
            name='Retry Template',
            category='development',
            config={},
            created_by=admin_user.id,
            company_id=company.id,
            is_active=True
        )
        db_session.session.add(template)
        db_session.session.commit()

        action = TemplateActionSequence(
            template_id=template.id,
            action_id='retry-test',
            action_type='generate_ssh_key',
            display_name='SSH Key with Retry',
            category='security',
            parameters={'key_name': 'test_key'},
            order=1,
            enabled=True,
            retry_config={
                'max_attempts': 3,
                'retry_delay_seconds': 0,  # No delay for faster testing
                'exponential_backoff': False
            }
        )
        db_session.session.add(action)
        db_session.session.commit()

        # Mock validation to always pass
        mock_validate.return_value = True

        # Fail twice, succeed on third try
        mock_execute.side_effect = [
            Exception("First failure"),
            Exception("Second failure"),
            {'success': True, 'key_path': '/home/test/.ssh/key'}
        ]

        executor = ActionExecutor(test_workspace, template)
        execution = executor._execute_single_action(action)

        assert execution.status == 'completed'
        assert execution.attempt_number == 3
        assert mock_execute.call_count == 3


class TestActionExecutorRollback:
    """Test rollback functionality"""

    @patch('app.services.action_handlers.SSHKeyActionHandler.execute')
    @patch('app.services.action_handlers.SSHKeyActionHandler.rollback')
    @patch('app.services.action_handlers.GitCloneActionHandler.execute')
    def test_rollback_on_failure(self, mock_git_exec, mock_ssh_rollback, mock_ssh_exec,
                                 test_workspace, action_template, db_session):
        """Test rollback is called on failure"""
        # SSH succeeds, Git fails
        mock_ssh_exec.return_value = {
            'success': True,
            'private_key_path': '/home/test/.ssh/key',
            'key_created': True
        }
        mock_git_exec.side_effect = Exception("Git failed")
        mock_ssh_rollback.return_value = True

        executor = ActionExecutor(test_workspace, action_template)
        result = executor.execute_template_actions()

        assert result['success'] is False
        # Rollback should be called for completed SSH action
        mock_ssh_rollback.assert_called_once()

    @patch('app.services.action_handlers.SSHKeyActionHandler.execute')
    @patch('app.services.action_handlers.GitCloneActionHandler.execute')
    @patch('app.services.action_handlers.GitCloneActionHandler.rollback')
    @patch('app.services.action_handlers.CompletionMessageActionHandler.execute')
    def test_rollback_reverse_order(self, mock_completion, mock_git_rollback,
                                    mock_git_exec, mock_ssh_exec,
                                    test_workspace, action_template):
        """Test rollback happens in reverse order"""
        # All succeed except completion
        mock_ssh_exec.return_value = {'success': True, 'key_created': True}
        mock_git_exec.return_value = {'success': True, 'repo_cloned': True}
        mock_completion.side_effect = Exception("Completion failed")
        mock_git_rollback.return_value = True

        executor = ActionExecutor(test_workspace, action_template)
        result = executor.execute_template_actions()

        # Git should rollback (most recent successful action)
        mock_git_rollback.assert_called_once()


class TestActionExecutorConditions:
    """Test conditional action execution"""

    def test_skip_disabled_action(self, test_workspace, db_session, company, admin_user):
        """Test disabled actions are skipped"""
        template = WorkspaceTemplate(
            name='Conditional Template',
            category='development',
            config={},
            created_by=admin_user.id,
            company_id=company.id,
            is_active=True
        )
        db_session.session.add(template)
        db_session.session.commit()

        actions = [
            TemplateActionSequence(
                template_id=template.id,
                action_id='enabled-dir',
                action_type='create_directory',
                display_name='Create Directory',
                category='infrastructure',
                parameters={'path': '/tmp/test'},
                order=1,
                enabled=True
            ),
            TemplateActionSequence(
                template_id=template.id,
                action_id='disabled-dir',
                action_type='create_directory',
                display_name='Disabled Directory',
                category='infrastructure',
                parameters={'path': '/tmp/test2'},
                order=2,
                enabled=False  # Disabled!
            ),
            TemplateActionSequence(
                template_id=template.id,
                action_id='completion-msg',
                action_type='display_completion_message',
                display_name='Completion Message',
                category='notification',
                parameters={},
                order=3,
                enabled=True
            )
        ]

        for action in actions:
            db_session.session.add(action)
        db_session.session.commit()

        executor = ActionExecutor(test_workspace, template)

        with patch('app.services.action_handlers.DirectoryActionHandler.execute') as mock_dir, \
             patch('app.services.action_handlers.CompletionMessageActionHandler.execute') as mock_comp:
            mock_dir.return_value = {'success': True}
            mock_comp.return_value = {'success': True}

            result = executor.execute_template_actions()

            # Only 2 actions executed (disabled one skipped)
            assert len(result['completed_actions']) == 2
            assert mock_dir.call_count == 1  # Only called once


class TestActionExecutorVariableSubstitution:
    """Test variable substitution across actions"""

    @patch('app.services.action_handlers.GitCloneActionHandler.validate')
    @patch('subprocess.run')
    def test_variable_substitution_in_parameters(self, mock_run, mock_validate, test_workspace, action_template):
        """Test variables are substituted in action parameters"""
        action_sequence = TemplateActionSequence.query.filter_by(
            template_id=action_template.id,
            action_type='clone_git_repository'
        ).first()

        # Original parameter has {home_directory} variable
        assert '{home_directory}' in action_sequence.parameters['destination_path']

        # Mock validation to pass
        mock_validate.return_value = True

        # Mock subprocess calls for git operations
        mock_run.side_effect = [
            Mock(returncode=0, stdout='', stderr=''),  # git clone
            Mock(returncode=0, stdout='abc123', stderr=''),  # get commit hash
            Mock(returncode=0, stdout='main', stderr='')  # get branch
        ]

        executor = ActionExecutor(test_workspace, action_template)
        execution = executor._execute_single_action(action_sequence)

        # Check that substitution happened by examining the result
        assert execution.status == 'completed'
        result = execution.result
        # The execute method substitutes variables before running git clone
        # We verify by checking the git clone command had the substituted path
        clone_call = mock_run.call_args_list[0]
        clone_command = ' '.join(clone_call[0][0])
        assert '/home/testco_exec/project' in clone_command
        assert '{home_directory}' not in clone_command


class TestActionExecutorMetrics:
    """Test execution metrics and logging"""

    @patch('app.services.action_handlers.SSHKeyActionHandler.execute')
    def test_execution_timing_recorded(self, mock_execute, test_workspace, action_template, db_session):
        """Test execution timing is recorded"""
        mock_execute.return_value = {'success': True}

        action_sequence = TemplateActionSequence.query.filter_by(
            template_id=action_template.id,
            action_type='generate_ssh_key'
        ).first()

        executor = ActionExecutor(test_workspace, action_template)
        execution = executor._execute_single_action(action_sequence)

        assert execution.started_at is not None
        assert execution.completed_at is not None
        assert execution.completed_at >= execution.started_at

    @patch('app.services.action_handlers.SSHKeyActionHandler.execute')
    def test_error_message_captured(self, mock_execute, test_workspace, action_template):
        """Test error messages are captured"""
        error_msg = "SSH key generation failed: Permission denied"
        mock_execute.side_effect = Exception(error_msg)

        action_sequence = TemplateActionSequence.query.filter_by(
            template_id=action_template.id,
            action_type='generate_ssh_key'
        ).first()

        executor = ActionExecutor(test_workspace, action_template)
        execution = executor._execute_single_action(action_sequence)

        assert execution.status == 'failed'
        assert error_msg in execution.error_message
