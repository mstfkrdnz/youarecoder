"""
Workspace provisioning service - Simplified action-based version.
All template-specific logic moved to action-based system.
"""
import os
import subprocess
import secrets
import string
from typing import Dict, Optional
from flask import current_app
from app import db
from app.models import Workspace, WorkspaceTemplate
from app.services.traefik_manager import TraefikManager
from app.services.action_executor import ActionExecutor


class WorkspaceProvisionerError(Exception):
    """Base exception for workspace provisioning errors."""
    pass


class PortAllocationError(WorkspaceProvisionerError):
    """Raised when no available ports are found."""
    pass


class UserCreationError(WorkspaceProvisionerError):
    """Raised when Linux user creation fails."""
    pass


class CodeServerSetupError(WorkspaceProvisionerError):
    """Raised when code-server setup fails."""
    pass


class WorkspaceProvisioner:
    """
    Service for provisioning code-server workspaces with action-based templates.

    Core responsibilities:
    - Port allocation
    - Linux user creation
    - code-server installation and configuration
    - Systemd service setup
    - Disk quota management
    - Action-based template execution
    """

    def __init__(self):
        self.port_range_start = current_app.config['WORKSPACE_PORT_RANGE_START']
        self.port_range_end = current_app.config['WORKSPACE_PORT_RANGE_END']
        self.base_dir = current_app.config['WORKSPACE_BASE_DIR']
        self.traefik_manager = TraefikManager()

    def allocate_port(self) -> int:
        """
        Allocate next available port from the configured range.

        Returns:
            int: Available port number

        Raises:
            PortAllocationError: If no ports are available
        """
        used_ports = {ws.port for ws in Workspace.query.all()}

        for port in range(self.port_range_start, self.port_range_end + 1):
            if port not in used_ports:
                return port

        raise PortAllocationError(
            f"No available ports in range {self.port_range_start}-{self.port_range_end}"
        )

    def generate_password(self, length: int = 18) -> str:
        """Generate secure random password."""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    def create_linux_user(self, username: str, password: str) -> None:
        """
        Create Linux user for workspace.

        Args:
            username: Linux username
            password: User password

        Raises:
            UserCreationError: If user creation fails
        """
        try:
            # Create user with home directory
            subprocess.run([
                '/usr/sbin/useradd',
                '-m',  # Create home directory
                '-s', '/bin/bash',  # Set bash as shell
                '-d', f"{self.base_dir}/{username}",  # Set home directory
                username
            ], check=True, capture_output=True, text=True)

            # Set password
            subprocess.run([
                '/usr/sbin/chpasswd'
            ], input=f"{username}:{password}", text=True, check=True, capture_output=True)

            current_app.logger.info(f"Linux user created: {username}")

        except subprocess.CalledProcessError as e:
            raise UserCreationError(f"Failed to create Linux user: {e.stderr}")

    def install_code_server(self, username: str, port: int, password: str) -> None:
        """
        Install and configure code-server for user.

        Args:
            username: Linux username
            port: Port for code-server
            password: Code-server password

        Raises:
            CodeServerSetupError: If installation fails
        """
        try:
            home_dir = f"{self.base_dir}/{username}"
            config_dir = f"{home_dir}/.config/code-server"
            config_file = f"{config_dir}/config.yaml"

            # Create config directory
            subprocess.run([
                '/usr/bin/su', '-', username, '-c',
                f"mkdir -p {config_dir}"
            ], check=True, capture_output=True, text=True)

            # Create config file
            config_content = f"""bind-addr: 127.0.0.1:{port}
auth: password
password: {password}
cert: false
"""
            subprocess.run([
                '/usr/bin/su', '-', username, '-c',
                f"echo '{config_content}' > {config_file}"
            ], check=True, capture_output=True, text=True)

            current_app.logger.info(f"code-server configured for {username} on port {port}")

        except subprocess.CalledProcessError as e:
            raise CodeServerSetupError(f"Failed to configure code-server: {e.stderr}")

    def create_systemd_service(self, username: str, workspace_file_path: Optional[str] = None) -> None:
        """
        Create systemd service for code-server.

        Args:
            username: Linux username
            workspace_file_path: Optional path to workspace file

        Raises:
            CodeServerSetupError: If service creation fails
        """
        try:
            service_name = f"code-server@{username}.service"
            service_path = f"/etc/systemd/system/{service_name}"

            # Build ExecStart command
            exec_start = "/usr/bin/code-server"
            if workspace_file_path:
                exec_start += f" {workspace_file_path}"

            service_content = f"""[Unit]
Description=code-server for {username}
After=network.target

[Service]
Type=simple
User={username}
ExecStart={exec_start}
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
            # Write service file
            with open(service_path, 'w') as f:
                f.write(service_content)

            # Reload systemd and enable service
            subprocess.run(['/bin/systemctl', 'daemon-reload'], check=True, capture_output=True)
            subprocess.run(['/bin/systemctl', 'enable', service_name], check=True, capture_output=True)
            subprocess.run(['/bin/systemctl', 'start', service_name], check=True, capture_output=True)

            current_app.logger.info(f"Systemd service created and started: {service_name}")

        except (subprocess.CalledProcessError, IOError) as e:
            raise CodeServerSetupError(f"Failed to create systemd service: {str(e)}")

    def set_disk_quota(self, username: str, quota_gb: int) -> None:
        """
        Set disk quota for user.

        Args:
            username: Linux username
            quota_gb: Disk quota in GB
        """
        try:
            # Set user quota using setquota
            subprocess.run([
                '/usr/sbin/setquota',
                '-u', username,
                str(quota_gb * 1024 * 1024),  # Soft limit in KB
                str(quota_gb * 1024 * 1024),  # Hard limit in KB
                '0', '0',  # No inode limits
                '-a'  # All file systems
            ], check=True, capture_output=True, text=True)

            current_app.logger.info(f"Disk quota set for {username}: {quota_gb}GB")

        except subprocess.CalledProcessError as e:
            current_app.logger.warning(f"Failed to set disk quota: {e.stderr}")
            # Non-fatal error

    def provision_workspace(self, workspace: Workspace) -> Dict[str, any]:
        """
        Provision complete workspace with action-based template system.

        Args:
            workspace: Workspace model instance

        Returns:
            dict: Provisioning result with status and details

        Raises:
            WorkspaceProvisionerError: If provisioning fails
        """
        result = {
            'success': False,
            'workspace_id': workspace.id,
            'linux_user': workspace.linux_username,
            'port': workspace.port,
            'steps_completed': []
        }

        try:
            # Step 1: Create Linux user
            linux_password = self.generate_password()
            self.create_linux_user(workspace.linux_username, linux_password)
            result['steps_completed'].append('linux_user_created')

            # Step 2: Install and configure code-server
            self.install_code_server(
                workspace.linux_username,
                workspace.port,
                workspace.code_server_password
            )
            result['steps_completed'].append('code_server_configured')

            # Step 3: Create systemd service (workspace file determined later by template)
            self.create_systemd_service(workspace.linux_username)
            result['steps_completed'].append('systemd_service_created')

            # Step 4: Set disk quota
            self.set_disk_quota(workspace.linux_username, workspace.disk_quota_gb)
            result['steps_completed'].append('disk_quota_set')

            # Step 5: Execute action-based template (if specified)
            if workspace.template_id:
                template = WorkspaceTemplate.query.get(workspace.template_id)
                if template and template.is_active and template.is_action_based:
                    executor = ActionExecutor(workspace, template)
                    action_result = executor.execute_template_actions()

                    if action_result['success']:
                        result['steps_completed'].append('template_actions_executed')
                        result['template_result'] = action_result
                        current_app.logger.info(
                            f"Template {template.name} applied: {action_result['completed_actions']}"
                        )
                    else:
                        raise WorkspaceProvisionerError(
                            f"Template execution failed: {action_result.get('error')}"
                        )

            # Step 6: Configure Traefik routing
            traefik_result = self.traefik_manager.add_workspace_route(
                workspace.subdomain,
                workspace.port,
                username=workspace.linux_username,
                password=workspace.code_server_password
            )

            if traefik_result['success']:
                result['steps_completed'].append('traefik_route_added')
                result['workspace_url'] = traefik_result['url']
            else:
                raise WorkspaceProvisionerError(
                    f"Traefik configuration failed: {traefik_result.get('error')}"
                )

            # Update workspace status
            workspace.status = 'active'
            workspace.is_running = True
            workspace.last_started_at = db.func.now()
            db.session.commit()

            result['success'] = True
            result['message'] = f"Workspace {workspace.name} provisioned successfully"

            current_app.logger.info(f"Workspace provisioning complete: {workspace.id}")

            return result

        except WorkspaceProvisionerError as e:
            current_app.logger.error(f"Workspace provisioning failed: {str(e)}")
            result['error'] = str(e)

            # Cleanup on failure
            self.cleanup_failed_workspace(workspace, result['steps_completed'])

            workspace.status = 'failed'
            db.session.commit()

            raise

    def cleanup_failed_workspace(self, workspace: Workspace, steps_completed: list) -> None:
        """
        Cleanup partially created workspace after provisioning failure.

        Args:
            workspace: Workspace model instance
            steps_completed: List of successfully completed steps
        """
        current_app.logger.warning(f"Cleaning up failed workspace: {workspace.id}")

        try:
            # Cleanup in reverse order
            if 'traefik_route_added' in steps_completed:
                self.traefik_manager.remove_workspace_route(workspace.subdomain)

            if 'systemd_service_created' in steps_completed:
                service_name = f'code-server@{workspace.linux_username}.service'
                subprocess.run(['/bin/systemctl', 'stop', service_name], capture_output=True)
                subprocess.run(['/bin/systemctl', 'disable', service_name], capture_output=True)
                try:
                    os.remove(f"/etc/systemd/system/{service_name}")
                except FileNotFoundError:
                    pass

            if 'linux_user_created' in steps_completed:
                subprocess.run([
                    '/usr/sbin/userdel', '-r', workspace.linux_username
                ], capture_output=True, text=True)

            current_app.logger.info(f"Cleanup completed for workspace: {workspace.id}")

        except Exception as cleanup_error:
            current_app.logger.error(f"Cleanup failed: {str(cleanup_error)}")

    def deprovision_workspace(self, workspace: Workspace) -> Dict[str, any]:
        """
        Remove workspace and all associated resources.

        Args:
            workspace: Workspace to remove

        Returns:
            dict: Deprovisioning result
        """
        result = {'success': False, 'steps_completed': []}

        try:
            # Remove Traefik route
            traefik_result = self.traefik_manager.remove_workspace_route(workspace.subdomain)
            if traefik_result['success']:
                result['steps_completed'].append('traefik_route_removed')

            # Stop and disable systemd service
            service_name = f'code-server@{workspace.linux_username}.service'
            subprocess.run(['/bin/systemctl', 'stop', service_name], capture_output=True)
            subprocess.run(['/bin/systemctl', 'disable', service_name], capture_output=True)
            result['steps_completed'].append('service_stopped')

            # Remove service file
            try:
                os.remove(f"/etc/systemd/system/{service_name}")
                subprocess.run(['/bin/systemctl', 'daemon-reload'], check=True)
            except FileNotFoundError:
                pass

            # Remove Linux user and home directory
            subprocess.run([
                '/usr/sbin/userdel', '-r', workspace.linux_username
            ], check=True, capture_output=True, text=True)
            result['steps_completed'].append('user_removed')

            result['success'] = True
            result['message'] = f"Workspace {workspace.name} deprovisioned successfully"

            current_app.logger.info(f"Workspace deprovisioned: {workspace.id}")

            return result

        except Exception as e:
            current_app.logger.error(f"Deprovisioning failed: {str(e)}")
            result['error'] = str(e)
            raise WorkspaceProvisionerError(f"Deprovisioning failed: {str(e)}")
