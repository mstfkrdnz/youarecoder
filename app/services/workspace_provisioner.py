import time
"""
Workspace provisioning service - Simplified action-based version.
All template-specific logic moved to action-based system.
"""
import os
import subprocess
import secrets
import string
from typing import Dict, Optional, Any
from flask import current_app
from app import db
from app.models import Workspace, WorkspaceTemplate
from app.models import WorkspaceTemplate
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

        IMPORTANT: Authentication is disabled (--auth none) for all workspaces.
        Traefik provides HTTP Basic Auth at the reverse proxy layer.

        Args:
            username: Linux username
            port: Port for code-server
            password: Not used (kept for backwards compatibility)

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

            # Create config file WITHOUT authentication
            # Authentication is handled by Traefik reverse proxy
            config_content = f"""bind-addr: 127.0.0.1:{port}
auth: none
cert: false
"""
            subprocess.run([
                '/usr/bin/su', '-', username, '-c',
                f"echo '{config_content}' > {config_file}"
            ], check=True, capture_output=True, text=True)

            current_app.logger.info(f"code-server configured for {username} on port {port} (auth: none)")

        except subprocess.CalledProcessError as e:
            raise CodeServerSetupError(f"Failed to configure code-server: {e.stderr}")

    def create_systemd_service(self, username: str, port: int, workspace_file_path: Optional[str] = None) -> None:
        """
        Create systemd service for code-server using template-based approach.

        Uses code-server@.service template with per-instance drop-in configuration
        for PORT environment variable.

        Args:
            username: Linux username
            port: Port number for this workspace
            workspace_file_path: Optional path to workspace file (default: ~/odoo)

        Raises:
            CodeServerSetupError: If service creation fails
        """
        try:
            # Ensure template service file exists
            template_path = "/etc/systemd/system/code-server@.service"
            if not os.path.exists(template_path):
                self._create_systemd_template(workspace_file_path or "odoo")

            # Create drop-in directory for this instance
            dropin_dir = f"/etc/systemd/system/code-server@{username}.service.d"
            os.makedirs(dropin_dir, exist_ok=True)

            # Create environment override with PORT
            override_content = f"""[Service]
Environment="PORT={port}"
"""
            override_path = f"{dropin_dir}/override.conf"
            with open(override_path, 'w') as f:
                f.write(override_content)

            service_name = f"code-server@{username}.service"

            # Reload systemd, enable and start service
            subprocess.run(['/bin/systemctl', 'daemon-reload'], check=True, capture_output=True)
            subprocess.run(['/bin/systemctl', 'enable', service_name], check=True, capture_output=True)
            subprocess.run(['/bin/systemctl', 'start', service_name], check=True, capture_output=True)

            current_app.logger.info(f"Systemd service created and started: {service_name} on port {port}")

        except (subprocess.CalledProcessError, IOError) as e:
            raise CodeServerSetupError(f"Failed to create systemd service: {str(e)}")

    def _create_systemd_template(self, workspace_dir: str = "odoo") -> None:
        """
        Create template systemd service file for code-server if it doesn't exist.

        Args:
            workspace_dir: Directory name within user home (default: odoo)
        """
        template_content = f"""[Unit]
Description=code-server for workspace %i
After=network.target

[Service]
Type=simple
User=%i
WorkingDirectory=/home/%i/{workspace_dir}
ExecStart=/usr/bin/code-server --bind-addr 127.0.0.1:${{PORT}} --auth none .
Restart=always
RestartSec=10
StandardOutput=append:/home/%i/code-server.log
StandardError=append:/home/%i/code-server.log

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=false
ReadWritePaths=/home/%i

[Install]
WantedBy=multi-user.target
"""
        template_path = "/etc/systemd/system/code-server@.service"
        with open(template_path, 'w') as f:
            f.write(template_content)

        current_app.logger.info(f"Created systemd template: {template_path}")

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
            self.create_systemd_service(workspace.linux_username, workspace.port)
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

                    # Check if provisioning was paused for SSH verification
                    if action_result.get('paused_for_ssh'):
                        workspace.status = 'paused'
                        workspace.progress_message = 'Awaiting SSH key verification'
                        db.session.commit()
                        
                        result['success'] = True
                        result['paused'] = True
                        result['message'] = 'Provisioning paused for SSH verification'
                        result['steps_completed'].append('template_actions_paused')
                        result['template_result'] = action_result
                        
                        current_app.logger.info(
                            f"Provisioning paused for workspace {workspace.id} - awaiting SSH verification"
                        )
                        return result
                    
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


    def _verify_github_ssh(self, username: str) -> bool:
        """
        Verify SSH connection to GitHub for a Linux user.

        Args:
            username: Linux username

        Returns:
            True if SSH connection to GitHub works
        """
        try:
            # Test SSH connection to GitHub as the user
            result = subprocess.run([
                '/usr/bin/su', '-', username, '-c',
                'ssh -T git@github.com -o StrictHostKeyChecking=no -o ConnectTimeout=10'
            ], capture_output=True, text=True, timeout=15)

            # GitHub returns exit code 1 for successful authentication
            # with message "Hi username! You've successfully authenticated"
            if result.returncode == 1 and 'successfully authenticated' in result.stderr:
                current_app.logger.info(f"SSH verification successful for user {username}")
                return True

            current_app.logger.warning(
                f"SSH verification failed for {username}: {result.stderr}"
            )
            return False

        except Exception as e:
            current_app.logger.error(f"SSH verification error: {str(e)}")
            return False

    def resume_provisioning_after_ssh_verification(self, workspace: Workspace, user_id: int) -> Dict[str, Any]:
        """
        Resume provisioning workflow after SSH key has been verified.

        This method continues template action execution from where it was paused
        after SSH key generation.

        Args:
            workspace: Workspace to resume provisioning for
            user_id: ID of user triggering the resume

        Returns:
            Dict with resume result and workspace details
        """
        result = {
            'success': False,
            'workspace_id': workspace.id,
            'resumed_from_action': None
        }

        try:
            # Verify workspace is in correct state
            if workspace.provisioning_state != 'awaiting_ssh_verification':
                raise WorkspaceProvisionerError(
                    f"Workspace not awaiting SSH verification (state: {workspace.provisioning_state})"
                )

            # Mark SSH as verified in extra_data
            extra_data = workspace.extra_data or {}
            extra_data['ssh_verified'] = True
            extra_data['ssh_verified_at'] = time.time()
            extra_data['ssh_verified_by'] = user_id
            workspace.extra_data = extra_data

            # Update provisioning state back to 'provisioning'
            workspace.provisioning_state = 'provisioning'
            workspace.progress_message = 'Resuming after SSH verification'
            db.session.commit()

            current_app.logger.info(
                f"Resuming provisioning for workspace {workspace.id} after SSH verification"
            )

            # Get template and resume action execution
            template = WorkspaceTemplate.query.get(workspace.template_id)
            if not template:
                raise WorkspaceProvisionerError(f"Template {workspace.template_id} not found")

            # Create executor and resume from current position
            executor = ActionExecutor(workspace, template)

            # Execute remaining actions
            resume_result = executor.resume_from_current_step()

            if resume_result['success']:
                # Complete provisioning setup (Traefik, status updates)
                workspace.status = 'active'
                workspace.is_running = True
                workspace.last_started_at = db.func.now()
                workspace.provisioning_state = 'completed'
                db.session.commit()

                result['success'] = True
                result['message'] = 'Provisioning resumed and completed successfully'
                result['workspace_url'] = workspace.get_access_url()
                result['clone_result'] = resume_result.get('clone_result', {})

                current_app.logger.info(
                    f"Provisioning resumed successfully for workspace {workspace.id}"
                )
            else:
                raise WorkspaceProvisionerError(
                    f"Resume failed: {resume_result.get('error')}"
                )

            return result

        except Exception as e:
            current_app.logger.error(f"Failed to resume provisioning: {str(e)}")
            result['error'] = str(e)

            workspace.status = 'failed'
            workspace.provisioning_state = 'failed'
            db.session.commit()

            raise WorkspaceProvisionerError(f"Resume provisioning failed: {str(e)}")
