"""
Action Executor Engine
Orchestrates execution of template actions with dependency resolution
"""
import time
import traceback
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import defaultdict, deque

from app import db
from app.models import (
    Workspace, WorkspaceTemplate, TemplateActionSequence,
    WorkspaceActionExecution
)
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
from app.services.action_handlers import (
    SSHKeyActionHandler,
    GitCloneActionHandler,
    SystemPackagesActionHandler,
    PythonVenvActionHandler,
    HANDLER_REGISTRY = {
        'generate_ssh_key': SSHKeyActionHandler,
        'clone_git_repository': GitCloneActionHandler,
        'install_system_packages': SystemPackagesActionHandler,
        'create_python_venv': PythonVenvActionHandler,
        'install_pip_requirements': PipRequirementsActionHandler,
        'create_directory': DirectoryActionHandler,
        'write_configuration_file': ConfigFileActionHandler,
        'create_postgresql_database': PostgreSQLDatabaseActionHandler,
        'install_vscode_extensions': VSCodeExtensionsActionHandler,
        'set_environment_variables': EnvironmentVariablesActionHandler,
        'execute_shell_script': ShellScriptActionHandler,
        'display_completion_message': CompletionMessageActionHandler,
    }
    SystemPackagesActionHandler,
    PythonVenvActionHandler,
    PipRequirementsActionHandler,
)


class ActionExecutor:
    """
    Orchestrates action-based workspace provisioning.

    Features:
    - DAG-based dependency resolution
    - Parallel execution where possible (future enhancement)
    - Automatic rollback on fatal errors
    - Fine-grained progress tracking
    - Conditional action execution
    """

    # Handler registry - maps action_type to handler class
    HANDLER_REGISTRY = {
        'generate_ssh_key': SSHKeyActionHandler,
        'clone_git_repository': GitCloneActionHandler,
        # More handlers will be added as they're implemented
    }

    def __init__(self, workspace: Workspace, template: WorkspaceTemplate):
        """
        Initialize executor for a workspace and template.

        Args:
            workspace: Workspace instance
            template: WorkspaceTemplate instance with action sequences
        """
        self.workspace = workspace
        self.template = template
        self.completed_actions: List[WorkspaceActionExecution] = []
        self.failed_action: Optional[WorkspaceActionExecution] = None

    def execute_template_actions(self) -> Dict[str, Any]:
        """
        Execute all actions for the template.

        Returns:
            Dict with success status, completed actions, and error info
        """
        # Get all action sequences for this template, ordered by execution order
        action_sequences = TemplateActionSequence.query.filter_by(
            template_id=self.template.id,
            enabled=True
        ).order_by(TemplateActionSequence.order).all()

        if not action_sequences:
            return {
                'success': True,
                'message': 'No actions to execute',
                'completed_actions': []
            }

        # Resolve dependencies and create execution plan
        execution_plan = self._resolve_dependencies(action_sequences)

        # Execute actions in order
        for action_seq in execution_plan:
            # Check if action should be executed based on condition
            if not self._should_execute_action(action_seq):
                self._skip_action(action_seq)
                continue

            # Create execution record
            execution = WorkspaceActionExecution(
                workspace_id=self.workspace.id,
                template_id=self.template.id,
                action_sequence_id=action_seq.id,
                action_id=action_seq.action_id,
                action_type=action_seq.action_type,
                max_attempts=action_seq.retry_config.get('max_attempts', 1)
            )
            db.session.add(execution)
            db.session.commit()

            # Execute action with retry logic
            success = self._execute_action_with_retry(action_seq, execution)

            if success:
                self.completed_actions.append(execution)
            else:
                self.failed_action = execution

                # Check if this is a fatal error
                if action_seq.fatal_on_error:
                    # Rollback if configured
                    if self.template.rollback_on_fatal_error:
                        self._rollback_completed_actions()

                    return {
                        'success': False,
                        'error': f"Fatal error in action {action_seq.action_id}",
                        'failed_action': action_seq.action_id,
                        'completed_actions': [a.action_id for a in self.completed_actions],
                        'rolled_back': self.template.rollback_on_fatal_error
                    }
                else:
                    # Non-fatal error, continue execution
                    continue

        return {
            'success': True,
            'completed_actions': [a.action_id for a in self.completed_actions],
            'total_actions': len(execution_plan)
        }

    def _resolve_dependencies(self, action_sequences: List[TemplateActionSequence]) -> List[TemplateActionSequence]:
        """
        Resolve action dependencies and return execution order.

        Uses topological sort to handle dependencies while preserving
        explicit order values where possible.

        Args:
            action_sequences: List of action sequences to order

        Returns:
            Ordered list of action sequences
        """
        # Build dependency graph
        action_map = {seq.action_id: seq for seq in action_sequences}
        dependencies = defaultdict(list)
        in_degree = defaultdict(int)

        # Initialize all actions
        for seq in action_sequences:
            in_degree[seq.action_id] = 0

        # Build dependency edges
        for seq in action_sequences:
            deps = seq.dependencies or []
            for dep_id in deps:
                if dep_id in action_map:
                    dependencies[dep_id].append(seq.action_id)
                    in_degree[seq.action_id] += 1

        # Topological sort using Kahn's algorithm
        queue = deque([
            action_id for action_id in action_map.keys()
            if in_degree[action_id] == 0
        ])

        # Sort queue by action order for deterministic execution
        queue = deque(sorted(queue, key=lambda aid: action_map[aid].order))

        result = []

        while queue:
            # Get next action with no dependencies
            current_id = queue.popleft()
            result.append(action_map[current_id])

            # Process dependent actions
            for dependent_id in dependencies[current_id]:
                in_degree[dependent_id] -= 1
                if in_degree[dependent_id] == 0:
                    queue.append(dependent_id)

            # Keep queue sorted by order
            queue = deque(sorted(queue, key=lambda aid: action_map[aid].order))

        # Check for circular dependencies
        if len(result) != len(action_sequences):
            raise ValueError("Circular dependency detected in action sequences")

        return result

    def _should_execute_action(self, action_seq: TemplateActionSequence) -> bool:
        """
        Check if action should be executed based on runtime condition.

        Args:
            action_seq: Action sequence to check

        Returns:
            True if action should execute, False to skip
        """
        if not action_seq.condition:
            return True

        # Get handler class
        handler_class = self.HANDLER_REGISTRY.get(action_seq.action_type)
        if not handler_class:
            return True  # Execute if handler not found (will fail later)

        # Create handler instance
        handler = self._create_handler(handler_class)

        # Evaluate condition
        try:
            return handler.evaluate_condition(action_seq.condition)
        except Exception as e:
            # If condition evaluation fails, default to executing
            return True

    def _execute_action_with_retry(self,
                                   action_seq: TemplateActionSequence,
                                   execution: WorkspaceActionExecution) -> bool:
        """
        Execute action with retry logic.

        Args:
            action_seq: Action sequence to execute
            execution: Execution record to track

        Returns:
            True if successful, False if failed
        """
        # Get handler class
        handler_class = self.HANDLER_REGISTRY.get(action_seq.action_type)
        if not handler_class:
            error_msg = f"No handler registered for action type: {action_seq.action_type}"
            execution.mark_failed(error_msg)
            db.session.commit()
            return False

        # Create handler instance
        handler = self._create_handler(handler_class)

        # Get retry configuration
        retry_config = action_seq.retry_config or {}
        max_attempts = retry_config.get('max_attempts', 1)
        retry_delay = retry_config.get('retry_delay_seconds', 0)
        exponential_backoff = retry_config.get('exponential_backoff', False)

        # Execute with retries
        for attempt in range(1, max_attempts + 1):
            execution.attempt_number = attempt
            execution.mark_started()
            db.session.commit()

            start_time = time.time()

            try:
                # Validate parameters
                if not handler.validate(action_seq.parameters):
                    raise ValueError("Parameter validation failed")

                # Execute action
                result = handler.execute(action_seq.parameters)

                # Calculate duration
                duration = time.time() - start_time

                # Mark as completed
                execution.mark_completed(result=result, duration_seconds=duration)
                db.session.commit()

                return True

            except Exception as e:
                duration = time.time() - start_time
                error_msg = str(e)
                stack_trace = traceback.format_exc()

                if attempt < max_attempts:
                    # Calculate delay for retry
                    if exponential_backoff:
                        delay = retry_delay * (2 ** (attempt - 1))
                    else:
                        delay = retry_delay

                    # Wait before retry
                    if delay > 0:
                        time.sleep(delay)

                    # Continue to next attempt
                    continue
                else:
                    # Final attempt failed
                    execution.mark_failed(error_msg, stack_trace)
                    db.session.commit()
                    return False

        return False

    def _skip_action(self, action_seq: TemplateActionSequence):
        """
        Skip action and record as skipped.

        Args:
            action_seq: Action sequence to skip
        """
        execution = WorkspaceActionExecution(
            workspace_id=self.workspace.id,
            template_id=self.template.id,
            action_sequence_id=action_seq.id,
            action_id=action_seq.action_id,
            action_type=action_seq.action_type,
            status=WorkspaceActionExecution.STATUS_SKIPPED
        )
        db.session.add(execution)
        db.session.commit()

    def _rollback_completed_actions(self):
        """
        Rollback completed actions in reverse order.
        """
        # Reverse order for rollback
        for execution in reversed(self.completed_actions):
            try:
                # Get action sequence
                action_seq = TemplateActionSequence.query.get(execution.action_sequence_id)
                if not action_seq:
                    continue

                # Get handler class
                handler_class = self.HANDLER_REGISTRY.get(action_seq.action_type)
                if not handler_class:
                    continue

                # Create handler instance
                handler = self._create_handler(handler_class)

                # Attempt rollback
                execution.rollback_attempted = True
                success = handler.rollback(action_seq.parameters, execution.result or {})

                if success:
                    execution.rollback_successful = True
                    execution.status = WorkspaceActionExecution.STATUS_ROLLED_BACK
                else:
                    execution.rollback_successful = False
                    execution.rollback_error = "Rollback returned False"

                db.session.commit()

            except Exception as e:
                execution.rollback_attempted = True
                execution.rollback_successful = False
                execution.rollback_error = str(e)
                db.session.commit()

    def _create_handler(self, handler_class):
        """
        Create handler instance with workspace context.

        Args:
            handler_class: Handler class to instantiate

        Returns:
            Handler instance
        """
        return handler_class(
            workspace_id=self.workspace.id,
            workspace_name=self.workspace.name,
            linux_username=self.workspace.linux_username,
            home_directory=self.workspace.home_directory,
            user_email=self.workspace.user.email if self.workspace.user else None,
            user_id=self.workspace.user_id,
            company_name=self.workspace.company.name if self.workspace.company else None,
            subdomain=self.workspace.subdomain
        )
