"""
SSH Key Generation Action Handler
Generates ED25519 SSH key pairs for workspace
"""
import os
import subprocess
from typing import Dict, Any
from app.services.action_handlers.base import BaseActionHandler


class SSHKeyActionHandler(BaseActionHandler):
    """Generate SSH key pair for workspace"""

    REQUIRED_PARAMETERS = ['key_type']
    OPTIONAL_PARAMETERS = ['key_comment', 'key_path', 'add_github_to_known_hosts']

    DISPLAY_NAME = 'Generate SSH Key'
    CATEGORY = 'security'
    DESCRIPTION = 'Generates ED25519 or RSA SSH key pairs for secure authentication'

    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate SSH key pair.

        Args:
            parameters: {
                'key_type': 'ed25519' or 'rsa',
                'key_comment': Optional comment for key,
                'key_path': Optional path (defaults to ~/.ssh/id_ed25519),
                'add_github_to_known_hosts': Optional, default True
            }

        Returns:
            Dict with public_key and key_path
        """
        # Substitute variables
        params = self.substitute_variables(parameters)

        key_type = params['key_type']
        key_comment = params.get('key_comment', f'workspace-{self.workspace_id}')
        key_path = params.get('key_path', f'{self.home_directory}/.ssh/id_{key_type}')
        add_github = params.get('add_github_to_known_hosts', True)

        self.log_info(f"Generating {key_type} SSH key at {key_path}")

        # Mock mode: simulate SSH key generation
        if self.mock_mode:
            self.log_info("MOCK MODE: Simulating SSH key generation")
            mock_public_key = f"ssh-{key_type} AAAAB3NzaC1mock123456789== {key_comment}"
            return {
                'success': True,
                'public_key': mock_public_key,
                'private_key_path': key_path,
                'public_key_path': f'{key_path}.pub',
                'key_type': key_type,
                'mock': True
            }

        # Create .ssh directory
        ssh_dir = os.path.dirname(key_path)
        os.makedirs(ssh_dir, mode=0o700, exist_ok=True)
        self.log_info(f"Created .ssh directory: {ssh_dir}")

        # Generate SSH key
        cmd = [
            '/usr/bin/ssh-keygen',
            '-t', key_type,
            '-f', key_path,
            '-N', '',  # No passphrase
            '-C', key_comment
        ]

        if key_type == 'rsa':
            cmd.extend(['-b', '4096'])  # 4096-bit RSA

        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )
            self.log_info(f"SSH key generated successfully")

        except subprocess.CalledProcessError as e:
            self.log_error(f"SSH key generation failed: {e.stderr}")
            raise

        # Set correct permissions
        os.chmod(key_path, 0o600)  # Private key: rw-------
        os.chmod(f'{key_path}.pub', 0o644)  # Public key: rw-r--r--
        os.chmod(ssh_dir, 0o700)  # .ssh directory: rwx------

        # Set correct ownership (FIXED)
        import shutil
        shutil.chown(ssh_dir, user=self.linux_username, group=self.linux_username)
        shutil.chown(key_path, user=self.linux_username, group=self.linux_username)
        shutil.chown(f'{key_path}.pub', user=self.linux_username, group=self.linux_username)

        self.log_info("Set SSH key permissions and ownership")

        # Read public key
        with open(f'{key_path}.pub', 'r') as f:
            public_key = f.read().strip()

        # Add GitHub to known_hosts if requested
        if add_github:
            self._add_github_to_known_hosts(ssh_dir)

        return {
            'success': True,
            'public_key': public_key,
            'private_key_path': key_path,
            'public_key_path': f'{key_path}.pub',
            'key_type': key_type
        }

    def validate(self, parameters: Dict[str, Any]) -> bool:
        """Validate SSH key generation parameters"""
        # Validate required parameters
        self.validate_parameters(parameters)

        # Validate key type
        key_type = parameters['key_type']
        if key_type not in ['ed25519', 'rsa', 'ecdsa']:
            raise ValueError(f"Invalid key_type: {key_type}. Must be ed25519, rsa, or ecdsa")

        return True

    def rollback(self, parameters: Dict[str, Any], execution_result: Dict[str, Any]) -> bool:
        """Delete generated SSH keys"""
        if not execution_result.get('success'):
            return True  # Nothing to rollback

        try:
            private_key = execution_result.get('private_key_path')
            public_key = execution_result.get('public_key_path')

            if private_key and os.path.exists(private_key):
                os.remove(private_key)
                self.log_info(f"Deleted private key: {private_key}")

            if public_key and os.path.exists(public_key):
                os.remove(public_key)
                self.log_info(f"Deleted public key: {public_key}")

            return True

        except Exception as e:
            self.log_error(f"Rollback failed: {e}")
            return False

    def _add_github_to_known_hosts(self, ssh_dir: str):
        """Add GitHub to known_hosts file"""
        known_hosts_path = os.path.join(ssh_dir, 'known_hosts')

        # GitHub's SSH host keys (as of 2024)
        github_keys = [
            'github.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl',
            'github.com ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBEmKSENjQEezOmxkZMy7opKgwFB9nkt5YRrYMjNuG5N87uRgg6CLrbo5wAdT/y6v0mKV0U2w0WZ2YB/++Tpockg=',
            'github.com ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCj7ndNxQowgcQnjshcLrqPEiiphnt+VTTvDP6mHBL9j1aNUkY4Ue1gvwnGLVlOhGeYrnZaMgRK6+PKCUXaDbC7qtbW8gIkhL7aGCsOr/C56SJMy/BCZfxd1nWzAOxSDPgVsmerOBYfNqltV9/hWCqBywINIR+5dIg6JTJ72pcEpEjcYgXkE2YEFXV1JHnsKgbLWNlhScqb2UmyRkQyytRLtL+38TGxkxCflmO+5Z8CSSNY7GidjMIZ7Q4zMjA2n1nGrlTDkzwDCsw+wqFPGQA179cnfGWOWRVruj16z6XyvxvjJwbz0wQZ75XK5tKSb7FNyeIEs4TT4jk+S4dhPeAUC5y+bDYirYgM4GC7uEnztnZyaVWQ7B381AK4Qdrwt51ZqExKbQpTUNn+EjqoTwvqNj4kqx5QUCI0ThS/YkOxJCXmPUWZbhjpCg56i+2aB6CmK2JGhn57K5mj0MNdBXA4/WnwH6XoPWJzK5Nyu2zB3nVXkNHsqzQXz1e/0lnQLRE='
        ]

        with open(known_hosts_path, 'a') as f:
            for key in github_keys:
                f.write(f'{key}\n')

        os.chmod(known_hosts_path, 0o644)
        
        # Set ownership on known_hosts (FIXED)
        import shutil
        shutil.chown(known_hosts_path, user=self.linux_username, group=self.linux_username)
        
        self.log_info("Added GitHub to known_hosts")
