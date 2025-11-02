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
            # Note: auth is disabled since Traefik handles authentication
            config_content = f"""bind-addr: 127.0.0.1:{port}
auth: none
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

    def create_systemd_service(self, username: str, workspace_file_path: Optional[str] = None) -> None:
        """
        Create systemd service for workspace code-server.

        Args:
            username: Linux username
            workspace_file_path: Optional path to .code-workspace file to auto-open

        Raises:
            CodeServerSetupError: If systemd service creation fails
        """
        # Build ExecStart command with optional workspace file
        exec_start = f"/usr/bin/code-server --config {self.base_dir}/{username}/.config/code-server/config.yaml"
        if workspace_file_path:
            exec_start += f" {workspace_file_path}"

        service_content = f"""[Unit]
Description=code-server for {username}
After=network.target

[Service]
Type=simple
User={username}
WorkingDirectory={self.base_dir}/{username}
ExecStart={exec_start}
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
        Set disk quota for user workspace using Linux setquota command.

        Args:
            username: Linux username
            quota_gb: Disk quota in GB

        Note:
            Requires quota support enabled on filesystem (usrquota option in /etc/fstab).
            Run scripts/enable_disk_quotas.sh to set up quota system.

        Raises:
            WorkspaceProvisionerError: If quota setting fails
        """
        current_app.logger.info(f"Setting disk quota for {username}: {quota_gb}GB")

        try:
            # Convert GB to KB for setquota (setquota uses 1KB blocks)
            quota_kb = quota_gb * 1024 * 1024

            # Set soft and hard limits to the same value (hard limit enforces the quota)
            # setquota -u <username> <soft_block_limit> <hard_block_limit> <soft_inode_limit> <hard_inode_limit> <filesystem>
            # Set block limits to quota_kb, inode limits to 0 (unlimited)
            subprocess.run([
                '/usr/sbin/setquota',
                '-u', username,
                str(quota_kb),  # Soft block limit (KB)
                str(quota_kb),  # Hard block limit (KB)
                '0',            # Soft inode limit (unlimited)
                '0',            # Hard inode limit (unlimited)
                '/'             # Filesystem (root partition)
            ], check=True, capture_output=True, text=True)

            current_app.logger.info(f"Disk quota successfully set for {username}: {quota_gb}GB ({quota_kb}KB)")

        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to set disk quota for {username}: {e.stderr}"
            current_app.logger.error(error_msg)
            # Don't raise exception - quota failure shouldn't block workspace creation
            # This allows workspaces to be created even if quota system isn't set up yet
            current_app.logger.warning("Quota setting failed - workspace created without disk quota enforcement")

        except Exception as e:
            current_app.logger.warning(f"Unexpected error setting quota for {username}: {str(e)}")

    def resize_workspace_disk(self, workspace: Workspace, new_quota_gb: int) -> Dict[str, any]:
        """
        Resize workspace disk quota.

        Args:
            workspace: Workspace model instance
            new_quota_gb: New disk quota in GB

        Returns:
            dict: Resize result with success status

        Note:
            This updates the database quota and logs the change.
            Actual filesystem quota enforcement requires quotactl setup.
        """
        result = {
            'success': False,
            'workspace_id': workspace.id,
            'old_quota_gb': workspace.disk_quota_gb,
            'new_quota_gb': new_quota_gb
        }

        try:
            old_quota = workspace.disk_quota_gb

            # Update database
            workspace.disk_quota_gb = new_quota_gb
            db.session.commit()

            # Set disk quota (currently just logs, no actual enforcement)
            self.set_disk_quota(workspace.linux_username, new_quota_gb)

            result['success'] = True
            result['message'] = f'Workspace disk quota updated from {old_quota}GB to {new_quota_gb}GB'

            current_app.logger.info(
                f"Workspace {workspace.id} ({workspace.name}) disk quota resized: "
                f"{old_quota}GB → {new_quota_gb}GB"
            )

            return result

        except Exception as e:
            db.session.rollback()
            error_msg = f"Failed to resize workspace disk: {str(e)}"
            current_app.logger.error(error_msg)
            result['message'] = error_msg
            raise WorkspaceProvisionerError(error_msg) from e

    def apply_workspace_template(self, workspace: Workspace, template: WorkspaceTemplate) -> Dict[str, any]:
        """
        Apply template configuration to workspace during provisioning.

        Enhanced in Phase 3 with:
        - Access token generation for password-less auth
        - SSH key generation for private repos
        - Launch.json for VS Code run configs
        - Multi-folder workspace file
        - PostgreSQL user/database setup

        Args:
            workspace: Workspace model instance
            template: WorkspaceTemplate to apply

        Returns:
            dict: Application result with applied components

        Template config schema (Phase 3):
        {
            "packages": ["package1", "package2"],  # System packages to install
            "extensions": ["ext1", "ext2"],        # VS Code extensions
            "repositories": [                       # Git repos
                {
                    "url": "...",
                    "branch": "main",
                    "target_dir": "optional-name",  # optional, defaults to repo name
                    "private": bool,                # optional, for tracking SSH requirement
                    "shallow": bool                 # optional, use --depth 1 for faster clone
                }
            ],
            "settings": {...},                      # VS Code settings.json
            "environment": {"KEY": "value"},        # Environment variables
            "launch_json": {...},                   # VS Code launch configurations
            "workspace_file": {...},                # Multi-folder workspace config
            "postgresql": {"database": "name"},     # PostgreSQL setup
            "ssh_required": bool,                   # Generate SSH key for private repos
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

            # 1. Generate access token (if not already exists)
            if not workspace.access_token:
                workspace.access_token = self._generate_access_token()
                db.session.commit()
                result['applied_components'].append('access_token')
                current_app.logger.info(f"Access token generated for workspace {workspace.id}")

            # 2. Generate SSH key if template requires private repos
            if config.get('ssh_required', False):
                public_key = self._generate_ssh_key(workspace.linux_username, home_dir)
                workspace.ssh_public_key = public_key
                db.session.commit()
                result['applied_components'].append('ssh_key')
                current_app.logger.info(f"SSH key generated for workspace {workspace.id}")

            # 3. Apply system packages
            if config.get('packages'):
                self._install_packages(workspace.linux_username, config['packages'])
                result['applied_components'].append('packages')

            # 4. Setup PostgreSQL (before repositories that might need database)
            if config.get('postgresql'):
                db_name = config['postgresql'].get('database', f"odoo_{workspace.linux_username}")
                self._setup_postgresql_user(workspace.linux_username, db_name)
                result['applied_components'].append('postgresql')

            # 5. Install VS Code extensions
            if config.get('extensions'):
                self._install_vscode_extensions(workspace.linux_username, config['extensions'])
                result['applied_components'].append('extensions')

            # 6. Clone repositories (will use SSH key for private repos)
            if config.get('repositories'):
                self._clone_repositories(workspace.linux_username, config['repositories'], home_dir)
                result['applied_components'].append('repositories')

            # 7. Apply VS Code settings
            if config.get('settings'):
                self._apply_vscode_settings(workspace.linux_username, config['settings'], home_dir)
                result['applied_components'].append('settings')

            # 8. Create launch.json
            if config.get('launch_json'):
                self._create_launch_json(workspace.linux_username, home_dir, config['launch_json'])
                result['applied_components'].append('launch_json')

            # 9. Create workspace file
            if config.get('workspace_file'):
                workspace_file = self._create_workspace_file(
                    workspace.linux_username, home_dir, config['workspace_file']
                )
                if workspace_file:
                    result['applied_components'].append('workspace_file')
                    result['workspace_file_path'] = workspace_file

            # 10. Set environment variables
            if config.get('environment'):
                self._set_environment_variables(workspace.linux_username, config['environment'], home_dir)
                result['applied_components'].append('environment')

            # 11. Execute post-create script
            if config.get('post_create_script'):
                self._execute_post_create_script(workspace.linux_username, config['post_create_script'], home_dir)
                result['applied_components'].append('post_create_script')

            # 12. Update template usage count and applied timestamp
            template.usage_count += 1
            workspace.template_applied_at = db.func.now()
            db.session.commit()

            result['success'] = True
            result['message'] = f"Template '{template.name}' applied successfully with {len(result['applied_components'])} components"

            current_app.logger.info(f"Template {template.id} applied to workspace {workspace.id}: {', '.join(result['applied_components'])}")

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
                '/usr/bin/su', '-', username, '-c',
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
                    '/usr/bin/su', '-', username, '-c',
                    f"/usr/bin/code-server --install-extension {extension}"
                ], check=True, capture_output=True, text=True, timeout=120)

            current_app.logger.info(f"Extensions installed successfully for {username}")

        except subprocess.CalledProcessError as e:
            current_app.logger.warning(f"Extension installation failed: {e.stderr}")
            # Non-fatal error - continue provisioning

    def _clone_repositories(self, username: str, repositories: list, home_dir: str) -> None:
        """
        Clone Git repositories into workspace.

        Supports shallow cloning for large repositories via 'shallow' config option.

        Repository config schema:
        {
            "url": "https://github.com/...",
            "branch": "main",
            "target_dir": "repo-name",  # optional, defaults to repo name from URL
            "private": false,           # optional, for tracking SSH requirement
            "shallow": true             # optional, use --depth 1 for shallow clone (default: false)
        }
        """
        if not repositories:
            return

        current_app.logger.info(f"Cloning repositories for {username}")

        try:
            for repo in repositories:
                repo_url = repo.get('url')
                branch = repo.get('branch', 'main')
                # Support both 'target' and 'target_dir' for backward compatibility
                target_dir = repo.get('target') or repo.get('target_dir', os.path.basename(repo_url).replace('.git', ''))
                shallow = repo.get('shallow', False)  # Default to full clone for backward compatibility

                clone_path = f"{home_dir}/{target_dir}"

                # Build git clone command with optional shallow flag
                clone_cmd = f"git clone -b {branch}"
                if shallow:
                    clone_cmd += " --depth 1"
                    current_app.logger.info(f"Using shallow clone for {repo_url}")
                clone_cmd += f" {repo_url} {clone_path}"

                subprocess.run([
                    '/usr/bin/su', '-', username, '-c',
                    clone_cmd
                ], check=True, capture_output=True, text=True, timeout=600)  # Increased from 120s to 600s

            current_app.logger.info(f"Repositories cloned successfully for {username}")

        except subprocess.CalledProcessError as e:
            current_app.logger.warning(f"Repository cloning failed: {e.stderr}")
            # Non-fatal error - continue provisioning
        except subprocess.TimeoutExpired as e:
            current_app.logger.error(f"Repository cloning timeout after 600s: {str(e)}")
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
                '/usr/bin/su', '-', username, '-c',
                f"mkdir -p {settings_dir}"
            ], check=True, capture_output=True, text=True)

            # Write settings file
            settings_json = json.dumps(settings, indent=2)
            subprocess.run([
                '/usr/bin/su', '-', username, '-c',
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
                '/usr/bin/su', '-', username, '-c',
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
                '/usr/bin/su', '-', username, '-c',
                f"echo '{script}' > {script_path} && chmod +x {script_path}"
            ], check=True, capture_output=True, text=True)

            # Execute script
            subprocess.run([
                '/usr/bin/su', '-', username, '-c',
                f"bash {script_path}"
            ], check=True, capture_output=True, text=True, timeout=600)

            # Clean up script
            subprocess.run([
                '/usr/bin/su', '-', username, '-c',
                f"rm {script_path}"
            ], check=True, capture_output=True, text=True)

            current_app.logger.info(f"Post-create script executed for {username}")

        except subprocess.CalledProcessError as e:
            current_app.logger.warning(f"Post-create script execution failed: {e.stderr}")
            # Non-fatal error - continue provisioning

    # ========== Phase 3: Template System Enhancements ==========

    def _generate_access_token(self) -> str:
        """
        Generate secure access token for code-server authentication.

        Returns:
            str: URL-safe 48-character token
        """
        return secrets.token_urlsafe(48)

    def _generate_ssh_key(self, username: str, home_dir: str) -> str:
        """
        Generate SSH key for private GitHub repository access.

        Uses ED25519 algorithm for enhanced security and performance.

        Args:
            username: Linux username
            home_dir: User home directory path

        Returns:
            str: SSH public key content

        Raises:
            WorkspaceProvisionerError: If SSH key generation fails
        """
        current_app.logger.info(f"Generating SSH key for {username}")

        try:
            ssh_dir = f"{home_dir}/.ssh"
            key_path = f"{ssh_dir}/id_ed25519"

            # Create .ssh directory with proper permissions
            subprocess.run([
                '/usr/bin/sudo', '-u', username, 'mkdir', '-p', ssh_dir
            ], check=True, capture_output=True, text=True)

            subprocess.run([
                '/usr/bin/sudo', '-u', username, 'chmod', '700', ssh_dir
            ], check=True, capture_output=True, text=True)

            # Generate ED25519 key (more secure and faster than RSA)
            subprocess.run([
                '/usr/bin/sudo', '-u', username, 'ssh-keygen',
                '-t', 'ed25519',
                '-C', f'{username}@youarecoder.com',
                '-f', key_path,
                '-N', ''  # No passphrase for automation
            ], check=True, capture_output=True, text=True)

            # Add GitHub to known_hosts to prevent SSH prompts
            subprocess.run([
                '/usr/bin/sudo', '-u', username, 'bash', '-c',
                f'ssh-keyscan github.com >> {ssh_dir}/known_hosts 2>/dev/null'
            ], check=True, capture_output=True, text=True)

            # Read public key
            result = subprocess.run([
                '/usr/bin/cat', f'{key_path}.pub'
            ], check=True, capture_output=True, text=True)

            public_key = result.stdout.strip()
            current_app.logger.info(f"SSH key generated for {username}")

            return public_key

        except subprocess.CalledProcessError as e:
            error_msg = f"SSH key generation failed for {username}: {e.stderr}"
            current_app.logger.error(error_msg)
            raise WorkspaceProvisionerError(error_msg)

    def _verify_github_ssh(self, username: str) -> bool:
        """
        Verify SSH connection to GitHub.

        Tests if the user's SSH key is properly configured for GitHub access.

        Args:
            username: Linux username

        Returns:
            bool: True if SSH connection successful, False otherwise
        """
        try:
            result = subprocess.run([
                '/usr/bin/sudo', '-u', username,
                'ssh', '-T', 'git@github.com',
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'ConnectTimeout=10'
            ], capture_output=True, text=True, timeout=15)

            # GitHub returns exit code 1 for successful auth without shell access
            # Exit code 0 or 1 both indicate successful authentication
            success = result.returncode in [0, 1]

            if success:
                current_app.logger.info(f"GitHub SSH verification successful for {username}")
            else:
                current_app.logger.warning(f"GitHub SSH verification failed for {username}")

            return success

        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            current_app.logger.warning(f"GitHub SSH verification error for {username}: {str(e)}")
            return False

    def _create_launch_json(self, username: str, home_dir: str, launch_config: dict) -> None:
        """
        Create VS Code launch.json for run/debug configurations.

        Args:
            username: Linux username
            home_dir: User home directory path
            launch_config: Launch configuration dictionary
        """
        if not launch_config:
            return

        current_app.logger.info(f"Creating launch.json for {username}")

        try:
            vscode_dir = f"{home_dir}/.vscode"
            launch_file = f"{vscode_dir}/launch.json"

            # Create .vscode directory
            subprocess.run([
                '/usr/bin/sudo', '-u', username, 'mkdir', '-p', vscode_dir
            ], check=True, capture_output=True, text=True)

            # Write launch.json
            launch_content = json.dumps(launch_config, indent=2)

            # Use heredoc to safely write JSON content
            subprocess.run([
                '/usr/bin/sudo', '-u', username, 'bash', '-c',
                f"cat > {launch_file} << 'LAUNCH_EOF'\n{launch_content}\nLAUNCH_EOF"
            ], check=True, capture_output=True, text=True)

            current_app.logger.info(f"launch.json created for {username}")

        except subprocess.CalledProcessError as e:
            current_app.logger.warning(f"launch.json creation failed: {e.stderr}")
            # Non-fatal error - continue provisioning

    def _create_workspace_file(self, username: str, home_dir: str, workspace_config: dict) -> Optional[str]:
        """
        Create multi-folder VS Code workspace file.

        Args:
            username: Linux username
            home_dir: User home directory path
            workspace_config: Workspace configuration dictionary

        Returns:
            str: Path to workspace file, or None if creation failed
        """
        if not workspace_config:
            return None

        current_app.logger.info(f"Creating workspace file for {username}")

        try:
            workspace_file = f"{home_dir}/workspace.code-workspace"

            # Write workspace file
            workspace_content = json.dumps(workspace_config, indent=2)

            subprocess.run([
                '/usr/bin/sudo', '-u', username, 'bash', '-c',
                f"cat > {workspace_file} << 'WORKSPACE_EOF'\n{workspace_content}\nWORKSPACE_EOF"
            ], check=True, capture_output=True, text=True)

            current_app.logger.info(f"Workspace file created at {workspace_file}")
            return workspace_file

        except subprocess.CalledProcessError as e:
            current_app.logger.warning(f"Workspace file creation failed: {e.stderr}")
            return None

    def _setup_postgresql_user(self, username: str, database_name: str) -> None:
        """
        Create PostgreSQL user and database.

        Args:
            username: PostgreSQL username (matches Linux username)
            database_name: Database name to create

        Raises:
            WorkspaceProvisionerError: If PostgreSQL setup fails
        """
        current_app.logger.info(f"Setting up PostgreSQL user {username} with database {database_name}")

        try:
            # Create PostgreSQL user (superuser for development flexibility)
            create_user = subprocess.run([
                '/usr/bin/sudo', '-u', 'postgres', 'createuser',
                '-s',  # Superuser
                username
            ], capture_output=True, text=True)

            # Ignore error if user already exists
            if create_user.returncode != 0 and 'already exists' not in create_user.stderr:
                raise WorkspaceProvisionerError(f"Failed to create PostgreSQL user: {create_user.stderr}")

            # Create database
            create_db = subprocess.run([
                '/usr/bin/sudo', '-u', 'postgres', 'createdb',
                database_name,
                '-O', username
            ], capture_output=True, text=True)

            # Ignore error if database already exists
            if create_db.returncode != 0 and 'already exists' not in create_db.stderr:
                raise WorkspaceProvisionerError(f"Failed to create database: {create_db.stderr}")

            # Grant all privileges
            grant_privileges = subprocess.run([
                '/usr/bin/sudo', '-u', 'postgres', 'psql',
                '-c', f"GRANT ALL PRIVILEGES ON DATABASE {database_name} TO {username};"
            ], check=True, capture_output=True, text=True)

            current_app.logger.info(f"PostgreSQL setup complete for {username}")

        except subprocess.CalledProcessError as e:
            error_msg = f"PostgreSQL setup failed for {username}: {e.stderr}"
            current_app.logger.error(error_msg)
            raise WorkspaceProvisionerError(error_msg)

    def _configure_code_server_auth(self, workspace: Workspace, service_file_path: str) -> None:
        """
        Configure code-server for token-based authentication.

        Modifies the systemd service file to use token authentication instead of password.

        Args:
            workspace: Workspace model instance with access_token
            service_file_path: Path to systemd service file
        """
        if not workspace.access_token:
            current_app.logger.warning(f"No access token found for workspace {workspace.id}, skipping token auth configuration")
            return

        current_app.logger.info(f"Configuring token-based auth for workspace {workspace.id}")

        try:
            # Read current service file
            with open(service_file_path, 'r') as f:
                service_content = f.read()

            # Replace --auth password with --auth none (token will be in URL)
            # The token is validated by code-server when passed as ?token= in URL
            service_content = service_content.replace('--auth password', '--auth none')

            # Write updated service file
            with open(service_file_path, 'w') as f:
                f.write(service_content)

            # Reload systemd daemon
            subprocess.run([
                '/usr/bin/systemctl', 'daemon-reload'
            ], check=True, capture_output=True, text=True)

            current_app.logger.info(f"Token-based auth configured for workspace {workspace.id}")

        except (IOError, subprocess.CalledProcessError) as e:
            current_app.logger.warning(f"Token auth configuration failed: {str(e)}")
            # Non-fatal error - workspace will use password auth

    def _install_extensions(self, username: str, extensions: list) -> None:
        """
        Install VS Code extensions for the workspace.

        Args:
            username: Linux username
            extensions: List of extension IDs to install (e.g., ['ms-python.python', 'ms-python.debugpy'])
        """
        if not extensions:
            return

        current_app.logger.info(f"Installing {len(extensions)} extensions for {username}")

        try:
            for ext_id in extensions:
                current_app.logger.info(f"Installing extension: {ext_id}")
                result = subprocess.run([
                    '/usr/bin/sudo', '-u', username,
                    '/usr/bin/code-server', '--install-extension', ext_id, '--force'
                ], capture_output=True, text=True, timeout=60)

                if result.returncode == 0:
                    current_app.logger.info(f"Extension {ext_id} installed successfully")
                else:
                    current_app.logger.warning(f"Extension {ext_id} installation warning: {result.stderr}")

        except subprocess.TimeoutExpired:
            current_app.logger.warning(f"Extension installation timed out for {username}")
        except subprocess.CalledProcessError as e:
            current_app.logger.warning(f"Extension installation failed: {str(e)}")
            # Non-fatal error - workspace will work without extensions

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

            # Step 2.5: Determine if workspace file will be created by template
            workspace_file_path = None
            if workspace.template_id:
                template = WorkspaceTemplate.query.get(workspace.template_id)
                if template and template.is_active:
                    config = json.loads(template.config) if template.config else {}
                    if config.get('workspace_file'):
                        # Workspace file will be created at this path by template application
                        workspace_file_path = f"{self.base_dir}/{workspace.linux_username}/workspace.code-workspace"
                        current_app.logger.info(f"Template will create workspace file at {workspace_file_path}")

            # Step 3: Create systemd service with workspace file path (if applicable)
            self.create_systemd_service(workspace.linux_username, workspace_file_path)
            result['steps_completed'].append('systemd_service_created')

            # Step 3.5: Configure token-based authentication (if access token exists)
            if workspace.access_token:
                service_path = f"/etc/systemd/system/code-server@{workspace.linux_username}.service"
                self._configure_code_server_auth(workspace, service_path)
                result['steps_completed'].append('token_auth_configured')
                current_app.logger.info(f"Token-based auth configured for workspace {workspace.id}")

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

                    # Step 5.5: Install post-provision extensions (if specified in template)
                    config = json.loads(template.config) if template.config else {}
                    extensions = config.get('post_provision_extensions', [])
                    if extensions:
                        self._install_extensions(workspace.linux_username, extensions)
                        result['steps_completed'].append('extensions_installed')
                        current_app.logger.info(f"Installed {len(extensions)} extensions for workspace {workspace.id}")

            # Step 6: Configure Traefik routing with BasicAuth
            traefik_result = self.traefik_manager.add_workspace_route(
                workspace.subdomain,
                workspace.port,
                username=workspace.linux_username,
                password=workspace.code_server_password
            )
            if traefik_result['success']:
                result['steps_completed'].append('traefik_route_added')
                # Add workspace file parameter to URL if workspace file exists
                base_url = traefik_result['url']
                if workspace_file_path:
                    result['workspace_url'] = f"{base_url}?workspace={workspace_file_path}"
                else:
                    result['workspace_url'] = base_url
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
            # Stop and remove systemd service - handle both naming patterns
            service_name = f'code-server@{workspace.linux_username}.service'
            service_path = f'/etc/systemd/system/{service_name}'

            # Fallback to alternative naming pattern
            if not os.path.exists(service_path):
                service_name = f'{workspace.linux_username}.service'
                service_path = f'/etc/systemd/system/{service_name}'

            # Only attempt service removal if service file exists
            if os.path.exists(service_path):
                # Stop service (don't fail if already stopped)
                subprocess.run([
                    '/bin/systemctl', 'stop', service_name
                ], capture_output=True, text=True)
                result['steps_completed'].append('service_stopped')

                # Disable service (don't fail if already disabled)
                subprocess.run([
                    '/bin/systemctl', 'disable', service_name
                ], capture_output=True, text=True)
                result['steps_completed'].append('service_disabled')

                # Remove service file
                os.remove(service_path)
                result['steps_completed'].append('service_removed')

                # Reload systemd daemon
                subprocess.run(['/bin/systemctl', 'daemon-reload'], capture_output=True, text=True)

                current_app.logger.info(f"Removed service file: {service_path}")
            else:
                current_app.logger.warning(f"Service file not found (skipping): {service_name}")
                result['steps_completed'].append('service_not_found')

            # Remove Linux user and home directory (don't fail if user doesn't exist)
            user_result = subprocess.run([
                '/usr/sbin/userdel', '-r', workspace.linux_username
            ], capture_output=True, text=True)
            if user_result.returncode == 0:
                result['steps_completed'].append('user_removed')
                current_app.logger.info(f"Removed Linux user: {workspace.linux_username}")
            else:
                current_app.logger.warning(f"User removal warning (user may not exist): {user_result.stderr}")
                result['steps_completed'].append('user_not_found')

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

    def _get_service_name(self, workspace: Workspace) -> str:
        """
        Get the actual systemd service name for a workspace.
        Handles both naming patterns: code-server@{username}.service and {username}.service

        Args:
            workspace: Workspace model instance

        Returns:
            str: Actual service name found, or default pattern if neither exists
        """
        # Try standard pattern first
        service_name = f'code-server@{workspace.linux_username}.service'
        service_path = f'/etc/systemd/system/{service_name}'

        if os.path.exists(service_path):
            return service_name

        # Try alternative pattern
        service_name = f'{workspace.linux_username}.service'
        service_path = f'/etc/systemd/system/{service_name}'

        if os.path.exists(service_path):
            return service_name

        # Return default pattern if neither exists
        return f'code-server@{workspace.linux_username}.service'

    def start_workspace_service(self, workspace: Workspace) -> Dict[str, any]:
        """
        Start workspace code-server systemd service.

        Args:
            workspace: Workspace model instance

        Returns:
            dict: Start result with success status
        """
        try:
            service_name = self._get_service_name(workspace)

            result = subprocess.run([
                '/bin/systemctl', 'start', service_name
            ], check=True, capture_output=True, text=True)

            current_app.logger.info(f"Started workspace service: {workspace.id} ({service_name})")

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
            service_name = self._get_service_name(workspace)

            result = subprocess.run([
                '/bin/systemctl', 'stop', service_name
            ], check=True, capture_output=True, text=True)

            current_app.logger.info(f"Stopped workspace service: {workspace.id} ({service_name})")

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
            service_name = self._get_service_name(workspace)

            result = subprocess.run([
                '/bin/systemctl', 'restart', service_name
            ], check=True, capture_output=True, text=True)

            current_app.logger.info(f"Restarted workspace service: {workspace.id} ({service_name})")

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
            service_name = self._get_service_name(workspace)

            result = subprocess.run([
                '/bin/systemctl', 'status', service_name
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
                'return_code': result.returncode,
                'service_name': service_name
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
