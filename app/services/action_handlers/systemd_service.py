"""
Systemd User Service Action Handler

Manages systemd user services for workspace processes.
"""

import os
import logging
from typing import Dict, Any, Optional
from .base import BaseActionHandler

logger = logging.getLogger(__name__)

class SystemdServiceActionHandler(BaseActionHandler):
    """
    Handler for managing systemd user services.

    Creates and manages systemd user service units for workspace processes.
    """

    REQUIRED_PARAMETERS = ['service_name', 'exec_start']
    OPTIONAL_PARAMETERS = [
        'description',
        'working_directory',
        'environment',
        'restart',
        'restart_sec',
        'enabled',
        'user',           # Service user (for system services)
        'group',          # Service group (optional)
        'user_mode',      # True for user service, False for system service (default: False)
        'after',          # Dependencies (list or string)
        'type',           # Service type (default: simple)
        'timeout_start_sec',  # Start timeout
        'standard_output',    # Logging output
        'standard_error'      # Logging error
    ]

    DISPLAY_NAME = 'Create Systemd Service'
    CATEGORY = 'service'
    DESCRIPTION = 'Creates and manages systemd service units for workspace processes with auto-restart'

    def execute(self, params: Dict[str, Any], workspace_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create and start a systemd service (user or system mode).

        Args:
            params: Action parameters including:
                - service_name: Name of the systemd service (required)
                - exec_start: Command to execute (required)
                - description: Service description (optional)
                - working_directory: Working directory for the service (optional)
                - environment: Dict of environment variables (optional)
                - restart: Restart policy (default: on-failure)
                - restart_sec: Seconds before restart (default: 3)
                - enabled: Whether to enable service at boot (default: true)
                - user: Service user (required for system services)
                - group: Service group (optional)
                - user_mode: True for user service, False for system (default: False)
                - after: Dependencies (list or string, default: network.target)
                - type: Service type (default: simple)
                - timeout_start_sec: Start timeout in seconds (optional)
                - standard_output: Output logging (optional, e.g., 'journal', 'append:/path/to/log')
                - standard_error: Error logging (optional)
            workspace_info: Workspace context information

        Returns:
            Dict with execution results
        """
        # Get parameters
        service_name = params['service_name']
        exec_start = params['exec_start']
        description = params.get('description', f'{service_name} service')
        working_directory = params.get('working_directory', workspace_info.get('home_directory', '~'))
        environment = params.get('environment', {})
        restart = params.get('restart', 'on-failure')
        restart_sec = params.get('restart_sec', 3)
        enabled = params.get('enabled', True)
        user = params.get('user')
        group = params.get('group')
        user_mode = params.get('user_mode', False)
        after_deps = params.get('after', ['network.target'])
        service_type = params.get('type', 'simple')
        timeout_start_sec = params.get('timeout_start_sec')
        standard_output = params.get('standard_output')
        standard_error = params.get('standard_error')

        # Validate system service requirements
        if not user_mode and not user:
            return {
                'success': False,
                'error': 'System services (user_mode=False) require "user" parameter'
            }

        # Replace placeholders in paths and commands
        exec_start = self.replace_placeholders(exec_start, workspace_info)
        working_directory = self.replace_placeholders(working_directory, workspace_info)
        if standard_output:
            standard_output = self.replace_placeholders(standard_output, workspace_info)
        if standard_error:
            standard_error = self.replace_placeholders(standard_error, workspace_info)

        # Build environment variables section
        env_lines = []
        if environment:
            for key, value in environment.items():
                value = self.replace_placeholders(str(value), workspace_info)
                env_lines.append(f'Environment="{key}={value}"')

        # Build After= dependencies
        if isinstance(after_deps, str):
            after_deps = [after_deps]
        after_line = f"After={' '.join(after_deps)}"

        # Create systemd service unit content
        service_lines = [
            "[Unit]",
            f"Description={description}",
            after_line,
            "",
            "[Service]",
            f"Type={service_type}",
        ]

        # Add User/Group for system services
        if not user_mode:
            service_lines.append(f"User={user}")
            if group:
                service_lines.append(f"Group={group}")

        service_lines.extend([
            f"WorkingDirectory={working_directory}",
            f"ExecStart={exec_start}",
            f"Restart={restart}",
            f"RestartSec={restart_sec}",
        ])

        # Add environment variables
        if env_lines:
            service_lines.extend(env_lines)

        # Add optional parameters
        if timeout_start_sec:
            service_lines.append(f"TimeoutStartSec={timeout_start_sec}")
        if standard_output:
            service_lines.append(f"StandardOutput={standard_output}")
        if standard_error:
            service_lines.append(f"StandardError={standard_error}")

        service_lines.extend([
            "",
            "[Install]",
            "WantedBy=multi-user.target" if not user_mode else "WantedBy=default.target",
            ""
        ])

        service_content = "\n".join(service_lines)

        # Determine service file path
        if user_mode:
            systemd_user_dir = os.path.expanduser('~/.config/systemd/user')
            service_file = os.path.join(systemd_user_dir, f'{service_name}.service')
            systemctl_cmd_prefix = 'systemctl --user'
        else:
            service_file = f'/etc/systemd/system/{service_name}.service'
            systemctl_cmd_prefix = 'systemctl'

        try:
            # Create directory if it doesn't exist (for user mode)
            if user_mode:
                os.makedirs(os.path.dirname(service_file), exist_ok=True)
            # For system services, /etc/systemd/system should already exist

            # Write service file
            with open(service_file, 'w') as f:
                f.write(service_content)

            logger.info(f"Created systemd service file: {service_file}")

            # Reload systemd daemon
            reload_result = self.run_command(f'{systemctl_cmd_prefix} daemon-reload')
            if reload_result['return_code'] != 0:
                return {
                    'success': False,
                    'error': f"Failed to reload systemd daemon: {reload_result.get('stderr', '')}"
                }

            # Enable service if requested
            if enabled:
                enable_result = self.run_command(f'{systemctl_cmd_prefix} enable {service_name}')
                if enable_result['return_code'] != 0:
                    logger.warning(f"Failed to enable service {service_name}: {enable_result.get('stderr', '')}")

            # Start the service
            start_result = self.run_command(f'{systemctl_cmd_prefix} start {service_name}')
            if start_result['return_code'] != 0:
                return {
                    'success': False,
                    'error': f"Failed to start service: {start_result.get('stderr', '')}"
                }

            # Verify service is running
            status_result = self.run_command(f'{systemctl_cmd_prefix} is-active {service_name}')
            is_active = status_result.get('stdout', '').strip() == 'active'

            return {
                'success': True,
                'service_name': service_name,
                'service_file': service_file,
                'status': 'active' if is_active else 'inactive',
                'enabled': enabled,
                'user_mode': user_mode,
                'message': f"Systemd service '{service_name}' created and started successfully"
            }

        except Exception as e:
            logger.error(f"Error creating systemd service: {str(e)}")
            return {
                'success': False,
                'error': f"Failed to create systemd service: {str(e)}"
            }

    def rollback(self, params: Dict[str, Any], workspace_info: Dict[str, Any], execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Rollback systemd service creation.

        Stops, disables, and removes the service file.

        Args:
            params: Original action parameters
            workspace_info: Workspace context information
            execution_result: Result from the execute() method

        Returns:
            Dict with rollback results
        """
        service_name = params['service_name']
        user_mode = params.get('user_mode', False)
        systemctl_cmd_prefix = 'systemctl --user' if user_mode else 'systemctl'

        try:
            # Stop the service (ignore errors if not running)
            stop_result = self.run_command(f'{systemctl_cmd_prefix} stop {service_name}')
            if stop_result['return_code'] != 0:
                logger.warning(f"Failed to stop service {service_name} (may not be running): {stop_result.get('stderr', '')}")

            # Disable the service (ignore errors if not enabled)
            disable_result = self.run_command(f'{systemctl_cmd_prefix} disable {service_name}')
            if disable_result['return_code'] != 0:
                logger.warning(f"Failed to disable service {service_name}: {disable_result.get('stderr', '')}")

            # Remove service file
            if user_mode:
                service_file = os.path.expanduser(f'~/.config/systemd/user/{service_name}.service')
            else:
                service_file = f'/etc/systemd/system/{service_name}.service'

            if os.path.exists(service_file):
                os.remove(service_file)
                logger.info(f"Removed systemd service file: {service_file}")

            # Reload systemd daemon
            reload_result = self.run_command(f'{systemctl_cmd_prefix} daemon-reload')
            if reload_result['return_code'] != 0:
                logger.warning(f"Failed to reload systemd daemon: {reload_result.get('stderr', '')}")

            return {
                'success': True,
                'service_name': service_name,
                'message': f"Systemd service '{service_name}' rolled back successfully"
            }

        except Exception as e:
            logger.error(f"Error rolling back systemd service: {str(e)}")
            return {
                'success': False,
                'error': f"Failed to rollback systemd service: {str(e)}"
            }
