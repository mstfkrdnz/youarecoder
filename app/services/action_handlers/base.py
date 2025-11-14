"""
Base Action Handler for workspace provisioning actions.
Provides common functionality for all action handlers.
"""
import os
import re
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pathlib import Path


class BaseActionHandler(ABC):
    """
    Abstract base class for all action handlers.
    Provides common functionality like variable substitution, condition evaluation,
    retry logic, validation, and logging.
    """

    # Subclasses should override these if they have specific parameters
    REQUIRED_PARAMETERS: List[str] = []
    OPTIONAL_PARAMETERS: List[str] = []

    # Metadata - override in subclasses for UI display
    DISPLAY_NAME: str = None
    CATEGORY: str = 'general'
    DESCRIPTION: str = None

    @classmethod
    def get_display_name(cls) -> str:
        """Return human-readable action name."""
        if cls.DISPLAY_NAME:
            return cls.DISPLAY_NAME
        # Fallback: generate from class name
        return cls.__name__.replace('ActionHandler', '').replace('_', ' ')

    @classmethod
    def get_category(cls) -> str:
        """Return action category."""
        return cls.CATEGORY

    @classmethod
    def get_description(cls) -> str:
        """Return action description."""
        if cls.DESCRIPTION:
            return cls.DESCRIPTION
        return cls.__doc__ or ''

    @classmethod
    def get_parameters_schema(cls) -> Dict[str, Any]:
        """
        Return detailed JSON schema for parameters with type and label metadata.

        Generates user-friendly labels from parameter names automatically.
        Subclasses can override PARAMETERS_METADATA to provide custom configurations.

        Returns:
            Dict mapping parameter names to their schema:
            {
                'param_name': {
                    'type': 'text|textarea|number|checkbox|select',
                    'label': 'Human Readable Label',
                    'required': True|False,
                    'default': default_value (optional),
                    'options': [] (for select type)
                }
            }
        """
        # Check if subclass provides custom metadata
        if hasattr(cls, 'PARAMETERS_METADATA'):
            return cls.PARAMETERS_METADATA

        # Auto-generate schema from parameter names
        schema = {}

        # Helper to generate label from parameter name
        def generate_label(param_name: str) -> str:
            """Convert param_name to Human Readable Label"""
            return ' '.join(word.capitalize() for word in param_name.replace('_', ' ').split())

        # Helper to infer type from parameter name
        def infer_type(param_name: str) -> str:
            """Infer input type from parameter name"""
            name_lower = param_name.lower()

            # Boolean parameters
            if name_lower.startswith('is_') or name_lower.startswith('enabled') or \
               name_lower.startswith('fatal') or name_lower in ['recursive', 'force', 'debug']:
                return 'checkbox'

            # Number parameters
            if any(x in name_lower for x in ['port', 'timeout', 'retry', 'max', 'min', 'count', 'depth', 'quota']):
                return 'number'

            # Text area for long content
            if any(x in name_lower for x in ['content', 'script', 'template', 'config_data', 'message']):
                return 'textarea'

            # Default to text input
            return 'text'

        # Process required parameters
        for param in cls.REQUIRED_PARAMETERS:
            schema[param] = {
                'type': infer_type(param),
                'label': generate_label(param),
                'required': True
            }

        # Process optional parameters
        for param in cls.OPTIONAL_PARAMETERS:
            schema[param] = {
                'type': infer_type(param),
                'label': generate_label(param),
                'required': False
            }

            # Add sensible defaults for common parameters
            if param == 'branch':
                schema[param]['default'] = 'main'
            elif param == 'depth':
                schema[param]['default'] = 0
            elif param.startswith('is_') or param in ['recursive', 'force', 'debug']:
                schema[param]['default'] = False

        return schema

    def __init__(self,
                 workspace_id: int,
                 workspace_name: str,
                 linux_username: str,
                 home_directory: str,
                 user_email: Optional[str] = None,
                 user_id: Optional[int] = None,
                 company_name: Optional[str] = None,
                 subdomain: Optional[str] = None,
                 port: Optional[int] = None):
        """
        Initialize action handler with workspace context.

        Args:
            workspace_id: Workspace database ID
            workspace_name: Workspace name
            linux_username: Linux system username
            home_directory: Home directory path
            user_email: Optional user email
            user_id: Optional user ID
            company_name: Optional company name
            subdomain: Optional workspace subdomain
            port: Optional workspace port for code-server
        """
        self.workspace_id = workspace_id
        self.workspace_name = workspace_name
        self.linux_username = linux_username
        self.home_directory = home_directory
        self.user_email = user_email
        self.user_id = user_id
        self.company_name = company_name
        self.subdomain = subdomain
        self.port = port

        # Logging
        self.logger = logging.getLogger(self.__class__.__name__)
        self._logs: List[Dict[str, Any]] = []

    @abstractmethod
    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the action with given parameters.
        Must be implemented by subclasses.

        Args:
            parameters: Action parameters after variable substitution

        Returns:
            Dict with execution results and metadata

        Raises:
            Exception: On execution failure
        """
        pass

    @abstractmethod
    def validate(self, parameters: Dict[str, Any]) -> bool:
        """
        Validate parameters before execution.
        Must be implemented by subclasses.

        Args:
            parameters: Action parameters to validate

        Returns:
            True if valid, False otherwise

        Raises:
            ValueError: If validation fails
        """
        pass

    @abstractmethod
    def rollback(self, parameters: Dict[str, Any], execution_result: Dict[str, Any]) -> bool:
        """
        Rollback changes made by this action.
        Must be implemented by subclasses.

        Args:
            parameters: Original action parameters
            execution_result: Result from execute() method

        Returns:
            True if rollback successful, False otherwise
        """
        pass

    def substitute_variables(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Substitute workspace variables in parameters.

        Supported variables:
        - {workspace_id} - Workspace database ID
        - {workspace_name} - Workspace name
        - {workspace_linux_username} - Linux username
        - {workspace_subdomain} - Workspace subdomain
        - {user_email} - User email address
        - {user_id} - User database ID
        - {company_name} - Company name
        - {home_directory} - Home directory path
        - {port} - Workspace port for code-server
        - ${HOME} - Home directory (shell style)
        - ${USER} - Linux username (shell style)

        Args:
            parameters: Parameters dict with variable placeholders

        Returns:
            Dict with variables substituted
        """
        substitution_map = {
            '{workspace_id}': str(self.workspace_id),
            '{workspace_name}': self.workspace_name,
            '{workspace_linux_username}': self.linux_username,
            '{workspace_subdomain}': self.subdomain or f'{self.linux_username}',
            '{user_email}': self.user_email or '',
            '{user_id}': str(self.user_id) if self.user_id else '',
            '{company_name}': self.company_name or '',
            '{home_directory}': self.home_directory,
            '{port}': str(self.port) if self.port else '',
            '${HOME}': self.home_directory,
            '${USER}': self.linux_username,
        }

        def substitute_value(value):
            """Recursively substitute variables in nested structures"""
            if isinstance(value, str):
                result = value
                for var, replacement in substitution_map.items():
                    result = result.replace(var, replacement)
                # Expand tilde
                if result.startswith('~/'):
                    result = f"{self.home_directory}/{result[2:]}"
                return result
            elif isinstance(value, dict):
                return {k: substitute_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [substitute_value(item) for item in value]
            else:
                return value

        return substitute_value(parameters)

    def evaluate_condition(self, condition: Dict[str, Any]) -> bool:
        """
        Evaluate runtime condition expression.

        Supported functions:
        - file_exists(path) - Check if file exists
        - directory_exists(path) - Check if directory exists
        - command_exists(cmd) - Check if command is available
        - env_var_set(var) - Check if environment variable is set

        Logical operators: AND, OR, NOT

        Args:
            condition: Condition configuration dict

        Returns:
            True if condition is met, False otherwise
        """
        expression = condition.get('expression', '')

        # Helper functions for condition evaluation
        def file_exists(path: str) -> bool:
            path = self.substitute_variables({'path': path})['path']
            return os.path.exists(path) and os.path.isfile(path)

        def directory_exists(path: str) -> bool:
            path = self.substitute_variables({'path': path})['path']
            return os.path.exists(path) and os.path.isdir(path)

        def command_exists(cmd: str) -> bool:
            import shutil
            return shutil.which(cmd) is not None

        def env_var_set(var_name: str) -> bool:
            return var_name in os.environ

        # Create evaluation context
        eval_context = {
            'file_exists': file_exists,
            'directory_exists': directory_exists,
            'command_exists': command_exists,
            'env_var_set': env_var_set,
        }

        try:
            # Safely evaluate expression
            result = eval(expression, {"__builtins__": {}}, eval_context)
            return bool(result)
        except Exception as e:
            self.log_error(f"Condition evaluation failed: {e}")
            return False

    def execute_with_retry(self,
                          parameters: Dict[str, Any],
                          retry_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute action with retry logic.

        Args:
            parameters: Action parameters
            retry_config: Retry configuration with max_attempts, retry_delay_seconds, exponential_backoff

        Returns:
            Execution result

        Raises:
            Exception: If all retry attempts fail
        """
        max_attempts = retry_config.get('max_attempts', 1)
        retry_delay = retry_config.get('retry_delay_seconds', 0)
        exponential_backoff = retry_config.get('exponential_backoff', False)

        last_error = None

        for attempt in range(1, max_attempts + 1):
            try:
                self.log_info(f"Attempt {attempt}/{max_attempts}")
                result = self.execute(parameters)
                return result

            except Exception as e:
                last_error = e
                self.log_error(f"Attempt {attempt} failed: {e}")

                if attempt < max_attempts:
                    # Calculate delay
                    if exponential_backoff:
                        delay = retry_delay * (2 ** (attempt - 1))
                    else:
                        delay = retry_delay

                    self.log_info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)

        # All attempts failed
        raise last_error

    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """
        Validate that all required parameters are present.

        Args:
            parameters: Parameters to validate

        Returns:
            True if valid

        Raises:
            ValueError: If required parameters are missing
        """
        missing = [p for p in self.REQUIRED_PARAMETERS if p not in parameters]

        if missing:
            raise ValueError(f"Missing required parameters: {', '.join(missing)}")

        return True

    def validate_result(self,
                       validation_config: Dict[str, Any],
                       execution_result: Dict[str, Any]) -> bool:
        """
        Validate execution result against validation configuration.

        Supported validations:
        - check_files_exist: List of files that must exist
        - check_directory_exists: Directory that must exist
        - check_permissions: Dict of {path: expected_permissions}

        Args:
            validation_config: Validation configuration
            execution_result: Result from execute()

        Returns:
            True if validation passes, False otherwise
        """
        # Check files exist
        files_to_check = validation_config.get('check_files_exist', [])
        for file_path in files_to_check:
            file_path = self.substitute_variables({'path': file_path})['path']
            if not os.path.exists(file_path):
                self.log_error(f"Validation failed: file not found: {file_path}")
                return False

        # Check directory exists
        dir_to_check = validation_config.get('check_directory_exists')
        if dir_to_check:
            dir_path = self.substitute_variables({'path': dir_to_check})['path']
            if not os.path.isdir(dir_path):
                self.log_error(f"Validation failed: directory not found: {dir_path}")
                return False

        # Check permissions
        permissions_to_check = validation_config.get('check_permissions', {})
        for path, expected_perms in permissions_to_check.items():
            path = self.substitute_variables({'path': path})['path']
            if os.path.exists(path):
                actual_perms = oct(os.stat(path).st_mode)[-3:]
                if actual_perms != expected_perms:
                    self.log_error(f"Validation failed: {path} has permissions {actual_perms}, expected {expected_perms}")
                    return False

        return True

    # Logging methods
    def log_info(self, message: str):
        """Log info message"""
        self.logger.info(message)
        self._logs.append({'level': 'info', 'message': message, 'timestamp': time.time()})

    def log_error(self, message: str):
        """Log error message"""
        self.logger.error(message)
        self._logs.append({'level': 'error', 'message': message, 'timestamp': time.time()})

    def log_warning(self, message: str):
        """Log warning message"""
        self.logger.warning(message)
        self._logs.append({'level': 'warning', 'message': message, 'timestamp': time.time()})

    def get_logs(self) -> List[Dict[str, Any]]:
        """Get all logs from this handler"""
        return self._logs
