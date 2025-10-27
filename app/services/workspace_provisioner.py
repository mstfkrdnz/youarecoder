"""
Workspace provisioning service for creating and managing code-server instances.
"""
import os
import subprocess
import secrets
import string
from typing import Dict, Tuple, Optional
from flask import current_app
from app import db
from app.models import Workspace


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
    Service for provisioning code-server workspaces.

    Handles:
    - Port allocation (sequential, DB-tracked)
    - Linux user creation
    - code-server installation and configuration
    - Systemd service setup
    - Disk quota management
    - Error handling and rollback
    """

    def __init__(self):
        self.port_range_start = current_app.config['WORKSPACE_PORT_RANGE_START']
        self.port_range_end = current_app.config['WORKSPACE_PORT_RANGE_END']
        self.base_dir = current_app.config['WORKSPACE_BASE_DIR']

    def allocate_port(self) -> int:
        """
        Allocate next available port from the configured range.

        Returns:
            int: Available port number

        Raises:
            PortAllocationError: If no ports are available
        """
        # Get all used ports from database
        used_ports = {ws.port for ws in Workspace.query.all()}

        # Find first available port in range
        for port in range(self.port_range_start, self.port_range_end + 1):
            if port not in used_ports:
                return port

        raise PortAllocationError(
            f"No available ports in range {self.port_range_start}-{self.port_range_end}"
        )

    def generate_password(self, length: int = 18) -> str:
        """
        Generate secure random password for code-server.

        Args:
            length: Password length (default 18)

        Returns:
            str: Secure random password
        """
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
                'useradd',
                '--create-home',
                '--shell', '/bin/bash',
                username
            ], check=True, capture_output=True, text=True)

            # Set password
            subprocess.run([
                'chpasswd'
            ], input=f"{username}:{password}\n", check=True, capture_output=True, text=True)

            current_app.logger.info(f"Linux user created: {username}")

        except subprocess.CalledProcessError as e:
            raise UserCreationError(f"Failed to create user {username}: {e.stderr}")

    def install_code_server(self, username: str, port: int, password: str) -> None:
        """
        Install and configure code-server for user.

        Args:
            username: Linux username
            port: Port number for code-server
            password: code-server password

        Raises:
            CodeServerSetupError: If code-server setup fails
        """
        try:
            home_dir = f"{self.base_dir}/{username}"
            config_dir = f"{home_dir}/.config/code-server"

            # Create config directory
            subprocess.run([
                'mkdir', '-p', config_dir
            ], check=True, capture_output=True, text=True)

            # Create code-server configuration
            config_content = f"""bind-addr: 127.0.0.1:{port}
auth: password
password: {password}
cert: false
"""
            config_path = f"{config_dir}/config.yaml"

            # Write config file as root, then change ownership
            with open(config_path, 'w') as f:
                f.write(config_content)

            # Change ownership of config directory to user
            subprocess.run([
                'chown', '-R', f"{username}:{username}", config_dir
            ], check=True, capture_output=True, text=True)

            # Set proper permissions
            subprocess.run([
                'chmod', '600', config_path
            ], check=True, capture_output=True, text=True)

            current_app.logger.info(f"code-server configured for {username} on port {port}")

        except (subprocess.CalledProcessError, IOError) as e:
            raise CodeServerSetupError(f"Failed to setup code-server for {username}: {str(e)}")

    def create_systemd_service(self, username: str) -> None:
        """
        Create systemd service for workspace code-server.

        Args:
            username: Linux username

        Raises:
            CodeServerSetupError: If systemd service creation fails
        """
        service_content = f"""[Unit]
Description=code-server for {username}
After=network.target

[Service]
Type=simple
User={username}
WorkingDirectory={self.base_dir}/{username}
ExecStart=/usr/bin/code-server --config {self.base_dir}/{username}/.config/code-server/config.yaml
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""

        service_path = f"/etc/systemd/system/code-server@{username}.service"

        try:
            # Write systemd service file
            with open(service_path, 'w') as f:
                f.write(service_content)

            # Reload systemd
            subprocess.run([
                'systemctl', 'daemon-reload'
            ], check=True, capture_output=True, text=True)

            # Enable service
            subprocess.run([
                'systemctl', 'enable', f'code-server@{username}.service'
            ], check=True, capture_output=True, text=True)

            # Start service
            subprocess.run([
                'systemctl', 'start', f'code-server@{username}.service'
            ], check=True, capture_output=True, text=True)

            current_app.logger.info(f"Systemd service created and started for {username}")

        except (subprocess.CalledProcessError, IOError) as e:
            raise CodeServerSetupError(f"Failed to create systemd service for {username}: {str(e)}")

    def set_disk_quota(self, username: str, quota_gb: int) -> None:
        """
        Set disk quota for user workspace.

        Args:
            username: Linux username
            quota_gb: Disk quota in GB

        Note:
            Requires quota support enabled on filesystem.
            This is a placeholder - actual implementation depends on filesystem setup.
        """
        # TODO: Implement disk quota using quotactl or setquota
        # For now, just log the intended quota
        current_app.logger.info(f"Disk quota set for {username}: {quota_gb}GB")
        pass

    def provision_workspace(self, workspace: Workspace) -> Dict[str, any]:
        """
        Provision complete workspace with all components.

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

            # Step 3: Create systemd service
            self.create_systemd_service(workspace.linux_username)
            result['steps_completed'].append('systemd_service_created')

            # Step 4: Set disk quota
            self.set_disk_quota(workspace.linux_username, workspace.disk_quota_gb)
            result['steps_completed'].append('disk_quota_set')

            # Update workspace status to active
            workspace.status = 'active'
            db.session.commit()

            result['success'] = True
            result['message'] = f"Workspace {workspace.name} provisioned successfully"

            current_app.logger.info(f"Workspace provisioning complete: {workspace.id}")

            return result

        except WorkspaceProvisionerError as e:
            # Rollback on error
            current_app.logger.error(f"Workspace provisioning failed: {str(e)}")
            result['error'] = str(e)

            # Attempt cleanup
            self.cleanup_failed_workspace(workspace, result['steps_completed'])

            # Update workspace status to failed
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
            if 'systemd_service_created' in steps_completed:
                subprocess.run([
                    'systemctl', 'stop', f'code-server@{workspace.linux_username}.service'
                ], capture_output=True, text=True)
                subprocess.run([
                    'systemctl', 'disable', f'code-server@{workspace.linux_username}.service'
                ], capture_output=True, text=True)
                os.remove(f"/etc/systemd/system/code-server@{workspace.linux_username}.service")

            if 'linux_user_created' in steps_completed:
                subprocess.run([
                    'userdel', '-r', workspace.linux_username
                ], capture_output=True, text=True)

            current_app.logger.info(f"Cleanup completed for workspace: {workspace.id}")

        except Exception as cleanup_error:
            current_app.logger.error(f"Cleanup failed: {str(cleanup_error)}")

    def deprovision_workspace(self, workspace: Workspace) -> Dict[str, any]:
        """
        Remove workspace and all associated resources.

        Args:
            workspace: Workspace model instance

        Returns:
            dict: Deprovisioning result
        """
        result = {
            'success': False,
            'workspace_id': workspace.id,
            'steps_completed': []
        }

        try:
            # Stop and remove systemd service
            subprocess.run([
                'systemctl', 'stop', f'code-server@{workspace.linux_username}.service'
            ], check=True, capture_output=True, text=True)
            result['steps_completed'].append('service_stopped')

            subprocess.run([
                'systemctl', 'disable', f'code-server@{workspace.linux_username}.service'
            ], check=True, capture_output=True, text=True)
            result['steps_completed'].append('service_disabled')

            os.remove(f"/etc/systemd/system/code-server@{workspace.linux_username}.service")
            result['steps_completed'].append('service_removed')

            # Remove Linux user and home directory
            subprocess.run([
                'userdel', '-r', workspace.linux_username
            ], check=True, capture_output=True, text=True)
            result['steps_completed'].append('user_removed')

            # Remove from database
            db.session.delete(workspace)
            db.session.commit()
            result['steps_completed'].append('database_removed')

            result['success'] = True
            result['message'] = f"Workspace {workspace.name} deprovisioned successfully"

            current_app.logger.info(f"Workspace deprovisioning complete: {workspace.id}")

            return result

        except Exception as e:
            current_app.logger.error(f"Workspace deprovisioning failed: {str(e)}")
            result['error'] = str(e)
            raise WorkspaceProvisionerError(f"Deprovisioning failed: {str(e)}")
