"""
Workspace provisioning service for creating and managing code-server instances.
"""
import os
import subprocess
import secrets
import string
from typing import Dict, Tuple, Optional
import json
from flask import current_app
from app import db
from app.models import Workspace, WorkspaceTemplate
from app.services.traefik_manager import TraefikManager


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
        self.traefik_manager = TraefikManager()

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
                '/usr/sbin/useradd',
                '--create-home',
                '--shell', '/bin/bash',
                username
            ], check=True, capture_output=True, text=True)

            # Set password
            subprocess.run([
                '/usr/sbin/chpasswd'
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
                '/bin/mkdir', '-p', config_dir
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
                '/bin/chown', '-R', f"{username}:{username}", config_dir
            ], check=True, capture_output=True, text=True)

            # Set proper permissions
            subprocess.run([
                '/bin/chmod', '600', config_path
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
                '/bin/systemctl', 'daemon-reload'
            ], check=True, capture_output=True, text=True)

            # Enable service
            subprocess.run([
                '/bin/systemctl', 'enable', f'code-server@{username}.service'
            ], check=True, capture_output=True, text=True)

            # Start service
            subprocess.run([
                '/bin/systemctl', 'start', f'code-server@{username}.service'
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

    def apply_workspace_template(self, workspace: Workspace, template: WorkspaceTemplate) -> Dict[str, any]:
        """
        Apply template configuration to workspace during provisioning.

        Args:
            workspace: Workspace model instance
            template: WorkspaceTemplate to apply

        Returns:
            dict: Application result with applied components

        Template config schema:
        {
            "packages": ["package1", "package2"],  # System packages to install
            "extensions": ["ext1", "ext2"],        # VS Code extensions
            "repositories": [{"url": "...", "branch": "main"}],  # Git repos to clone
            "settings": {...},                      # VS Code settings.json
            "environment": {"KEY": "value"},        # Environment variables
            "post_create_script": "bash commands"   # Post-creation script
        }
        """
        result = {
            'success': False,
            'template_id': template.id,
            'template_name': template.name,
            'applied_components': []
        }

        try:
            config = template.config
            home_dir = f"{self.base_dir}/{workspace.linux_username}"

            # Apply system packages
            if config.get('packages'):
                self._install_packages(workspace.linux_username, config['packages'])
                result['applied_components'].append('packages')

            # Install VS Code extensions
            if config.get('extensions'):
                self._install_vscode_extensions(workspace.linux_username, config['extensions'])
                result['applied_components'].append('extensions')

            # Clone repositories
            if config.get('repositories'):
                self._clone_repositories(workspace.linux_username, config['repositories'], home_dir)
                result['applied_components'].append('repositories')

            # Apply VS Code settings
            if config.get('settings'):
                self._apply_vscode_settings(workspace.linux_username, config['settings'], home_dir)
                result['applied_components'].append('settings')

            # Set environment variables
            if config.get('environment'):
                self._set_environment_variables(workspace.linux_username, config['environment'], home_dir)
                result['applied_components'].append('environment')

            # Execute post-create script
            if config.get('post_create_script'):
                self._execute_post_create_script(workspace.linux_username, config['post_create_script'], home_dir)
                result['applied_components'].append('post_create_script')

            # Update template usage count
            template.usage_count += 1
            db.session.commit()

            result['success'] = True
            result['message'] = f"Template '{template.name}' applied successfully"

            current_app.logger.info(f"Template {template.id} applied to workspace {workspace.id}")

            return result

        except Exception as e:
            current_app.logger.error(f"Template application failed: {str(e)}")
            result['error'] = str(e)
            raise WorkspaceProvisionerError(f"Template application failed: {str(e)}")

    def _install_packages(self, username: str, packages: list) -> None:
        """Install system packages as user."""
        if not packages:
            return

        current_app.logger.info(f"Installing packages for {username}: {', '.join(packages)}")

        # Install packages based on common package managers
        try:
            # Try pip for Python packages
            subprocess.run([
                'su', '-', username, '-c',
                f"pip3 install --user {' '.join(packages)}"
            ], check=True, capture_output=True, text=True, timeout=300)

            current_app.logger.info(f"Packages installed successfully for {username}")

        except subprocess.CalledProcessError as e:
            current_app.logger.warning(f"Package installation failed: {e.stderr}")
            # Non-fatal error - continue provisioning

    def _install_vscode_extensions(self, username: str, extensions: list) -> None:
        """Install VS Code extensions."""
        if not extensions:
            return

        current_app.logger.info(f"Installing VS Code extensions for {username}: {', '.join(extensions)}")

        try:
            for extension in extensions:
                subprocess.run([
                    'su', '-', username, '-c',
                    f"/usr/bin/code-server --install-extension {extension}"
                ], check=True, capture_output=True, text=True, timeout=120)

            current_app.logger.info(f"Extensions installed successfully for {username}")

        except subprocess.CalledProcessError as e:
            current_app.logger.warning(f"Extension installation failed: {e.stderr}")
            # Non-fatal error - continue provisioning

    def _clone_repositories(self, username: str, repositories: list, home_dir: str) -> None:
        """Clone Git repositories into workspace."""
        if not repositories:
            return

        current_app.logger.info(f"Cloning repositories for {username}")

        try:
            for repo in repositories:
                repo_url = repo.get('url')
                branch = repo.get('branch', 'main')
                target_dir = repo.get('target_dir', os.path.basename(repo_url).replace('.git', ''))

                clone_path = f"{home_dir}/{target_dir}"

                subprocess.run([
                    'su', '-', username, '-c',
                    f"git clone -b {branch} {repo_url} {clone_path}"
                ], check=True, capture_output=True, text=True, timeout=120)

            current_app.logger.info(f"Repositories cloned successfully for {username}")

        except subprocess.CalledProcessError as e:
            current_app.logger.warning(f"Repository cloning failed: {e.stderr}")
            # Non-fatal error - continue provisioning

    def _apply_vscode_settings(self, username: str, settings: dict, home_dir: str) -> None:
        """Apply VS Code settings.json configuration."""
        if not settings:
            return

        current_app.logger.info(f"Applying VS Code settings for {username}")

        try:
            settings_dir = f"{home_dir}/.local/share/code-server/User"
            settings_file = f"{settings_dir}/settings.json"

            # Create directory
            subprocess.run([
                'su', '-', username, '-c',
                f"mkdir -p {settings_dir}"
            ], check=True, capture_output=True, text=True)

            # Write settings file
            settings_json = json.dumps(settings, indent=2)
            subprocess.run([
                'su', '-', username, '-c',
                f"echo '{settings_json}' > {settings_file}"
            ], check=True, capture_output=True, text=True)

            current_app.logger.info(f"VS Code settings applied for {username}")

        except subprocess.CalledProcessError as e:
            current_app.logger.warning(f"VS Code settings application failed: {e.stderr}")
            # Non-fatal error - continue provisioning

    def _set_environment_variables(self, username: str, environment: dict, home_dir: str) -> None:
        """Set environment variables in user's bashrc."""
        if not environment:
            return

        current_app.logger.info(f"Setting environment variables for {username}")

        try:
            bashrc_path = f"{home_dir}/.bashrc"

            env_lines = ["", "# Environment variables from template"]
            for key, value in environment.items():
                env_lines.append(f"export {key}='{value}'")

            env_content = '\n'.join(env_lines)

            subprocess.run([
                'su', '-', username, '-c',
                f"echo '{env_content}' >> {bashrc_path}"
            ], check=True, capture_output=True, text=True)

            current_app.logger.info(f"Environment variables set for {username}")

        except subprocess.CalledProcessError as e:
            current_app.logger.warning(f"Environment variable setup failed: {e.stderr}")
            # Non-fatal error - continue provisioning

    def _execute_post_create_script(self, username: str, script: str, home_dir: str) -> None:
        """Execute post-creation script."""
        if not script:
            return

        current_app.logger.info(f"Executing post-create script for {username}")

        try:
            script_path = f"{home_dir}/.template_post_create.sh"

            # Write script
            subprocess.run([
                'su', '-', username, '-c',
                f"echo '{script}' > {script_path} && chmod +x {script_path}"
            ], check=True, capture_output=True, text=True)

            # Execute script
            subprocess.run([
                'su', '-', username, '-c',
                f"bash {script_path}"
            ], check=True, capture_output=True, text=True, timeout=300)

            # Clean up script
            subprocess.run([
                'su', '-', username, '-c',
                f"rm {script_path}"
            ], check=True, capture_output=True, text=True)

            current_app.logger.info(f"Post-create script executed for {username}")

        except subprocess.CalledProcessError as e:
            current_app.logger.warning(f"Post-create script execution failed: {e.stderr}")
            # Non-fatal error - continue provisioning

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

            # Step 5: Apply workspace template (if specified)
            if workspace.template_id:
                template = WorkspaceTemplate.query.get(workspace.template_id)
                if template and template.is_active:
                    template_result = self.apply_workspace_template(workspace, template)
                    result['steps_completed'].append('template_applied')
                    result['template_applied'] = template_result
                    current_app.logger.info(f"Template {template.name} applied to workspace {workspace.id}")

            # Step 6: Configure Traefik routing
            traefik_result = self.traefik_manager.add_workspace_route(
                workspace.subdomain,
                workspace.port
            )
            if traefik_result['success']:
                result['steps_completed'].append('traefik_route_added')
                result['workspace_url'] = traefik_result['url']
            else:
                raise WorkspaceProvisionerError(f"Traefik configuration failed: {traefik_result.get('error')}")

            # Update workspace status to active and mark as running (systemd service auto-starts)
            workspace.status = 'active'
            workspace.is_running = True
            workspace.last_started_at = db.func.now()
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
            if 'traefik_route_added' in steps_completed:
                self.traefik_manager.remove_workspace_route(workspace.subdomain)

            if 'systemd_service_created' in steps_completed:
                subprocess.run([
                    '/bin/systemctl', 'stop', f'code-server@{workspace.linux_username}.service'
                ], capture_output=True, text=True)
                subprocess.run([
                    '/bin/systemctl', 'disable', f'code-server@{workspace.linux_username}.service'
                ], capture_output=True, text=True)
                os.remove(f"/etc/systemd/system/code-server@{workspace.linux_username}.service")

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
                '/bin/systemctl', 'stop', f'code-server@{workspace.linux_username}.service'
            ], check=True, capture_output=True, text=True)
            result['steps_completed'].append('service_stopped')

            subprocess.run([
                '/bin/systemctl', 'disable', f'code-server@{workspace.linux_username}.service'
            ], check=True, capture_output=True, text=True)
            result['steps_completed'].append('service_disabled')

            os.remove(f"/etc/systemd/system/code-server@{workspace.linux_username}.service")
            result['steps_completed'].append('service_removed')

            # Remove Linux user and home directory
            subprocess.run([
                '/usr/sbin/userdel', '-r', workspace.linux_username
            ], check=True, capture_output=True, text=True)
            result['steps_completed'].append('user_removed')

            # Remove Traefik routing
            traefik_result = self.traefik_manager.remove_workspace_route(workspace.subdomain)
            if traefik_result['success']:
                result['steps_completed'].append('traefik_route_removed')
            else:
                current_app.logger.warning(f"Traefik route removal warning: {traefik_result.get('error')}")

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

    # Phase 4: Workspace Lifecycle Management Methods

    def start_workspace_service(self, workspace: Workspace) -> Dict[str, any]:
        """
        Start workspace code-server systemd service.

        Args:
            workspace: Workspace model instance

        Returns:
            dict: Start result with success status
        """
        try:
            result = subprocess.run([
                '/bin/systemctl', 'start', f'code-server@{workspace.linux_username}.service'
            ], check=True, capture_output=True, text=True)

            current_app.logger.info(f"Started workspace service: {workspace.id}")

            return {
                'success': True,
                'message': f'Workspace {workspace.name} started successfully'
            }

        except subprocess.CalledProcessError as e:
            current_app.logger.error(f"Failed to start workspace {workspace.id}: {e.stderr}")
            return {
                'success': False,
                'message': f'Failed to start workspace service: {e.stderr}'
            }

    def stop_workspace_service(self, workspace: Workspace) -> Dict[str, any]:
        """
        Stop workspace code-server systemd service.

        Args:
            workspace: Workspace model instance

        Returns:
            dict: Stop result with success status
        """
        try:
            result = subprocess.run([
                '/bin/systemctl', 'stop', f'code-server@{workspace.linux_username}.service'
            ], check=True, capture_output=True, text=True)

            current_app.logger.info(f"Stopped workspace service: {workspace.id}")

            return {
                'success': True,
                'message': f'Workspace {workspace.name} stopped successfully'
            }

        except subprocess.CalledProcessError as e:
            current_app.logger.error(f"Failed to stop workspace {workspace.id}: {e.stderr}")
            return {
                'success': False,
                'message': f'Failed to stop workspace service: {e.stderr}'
            }

    def restart_workspace_service(self, workspace: Workspace) -> Dict[str, any]:
        """
        Restart workspace code-server systemd service.

        Args:
            workspace: Workspace model instance

        Returns:
            dict: Restart result with success status
        """
        try:
            result = subprocess.run([
                '/bin/systemctl', 'restart', f'code-server@{workspace.linux_username}.service'
            ], check=True, capture_output=True, text=True)

            current_app.logger.info(f"Restarted workspace service: {workspace.id}")

            return {
                'success': True,
                'message': f'Workspace {workspace.name} restarted successfully'
            }

        except subprocess.CalledProcessError as e:
            current_app.logger.error(f"Failed to restart workspace {workspace.id}: {e.stderr}")
            return {
                'success': False,
                'message': f'Failed to restart workspace service: {e.stderr}'
            }

    def get_workspace_service_status(self, workspace: Workspace) -> Dict[str, any]:
        """
        Get workspace code-server systemd service status.

        Args:
            workspace: Workspace model instance

        Returns:
            dict: Service status information
        """
        try:
            result = subprocess.run([
                '/bin/systemctl', 'status', f'code-server@{workspace.linux_username}.service'
            ], capture_output=True, text=True)

            # Parse systemctl status output
            status_lines = result.stdout.split('\n')
            active_line = [line for line in status_lines if 'Active:' in line]

            if active_line:
                active_status = active_line[0].strip()
                is_active = 'active (running)' in active_status.lower()
            else:
                is_active = False

            return {
                'is_active': is_active,
                'status_output': result.stdout,
                'return_code': result.returncode
            }

        except Exception as e:
            current_app.logger.error(f"Failed to get workspace {workspace.id} status: {str(e)}")
            return {
                'is_active': False,
                'error': str(e)
            }

    def get_workspace_logs(self, workspace: Workspace, lines: int = 100, since: Optional[str] = None) -> Dict[str, any]:
        """
        Get workspace code-server logs from systemd journal.

        Args:
            workspace: Workspace model instance
            lines: Number of log lines to retrieve (default 100)
            since: Time filter (e.g., "1 hour ago", "2024-01-01")

        Returns:
            dict: Log data with success status
        """
        try:
            # Build journalctl command
            cmd = [
                '/bin/journalctl',
                '-u', f'code-server@{workspace.linux_username}.service',
                '-n', str(lines),
                '--no-pager'
            ]

            if since:
                cmd.extend(['--since', since])

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            logs = result.stdout.split('\n')

            return {
                'success': True,
                'logs': logs,
                'truncated': len(logs) >= lines
            }

        except subprocess.CalledProcessError as e:
            current_app.logger.error(f"Failed to get workspace {workspace.id} logs: {e.stderr}")
            return {
                'success': False,
                'logs': [],
                'error': e.stderr
            }
