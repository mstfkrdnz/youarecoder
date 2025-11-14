"""
Git Clone Action Handler
Clones Git repositories for workspace provisioning
"""
import os
import subprocess
import shutil
from typing import Dict, Any
from app.services.action_handlers.base import BaseActionHandler


class GitCloneActionHandler(BaseActionHandler):
    """Clone Git repository to workspace"""

    REQUIRED_PARAMETERS = ['repo_url', 'destination_path']
    OPTIONAL_PARAMETERS = ['branch', 'depth', 'use_ssh', 'recursive', 'is_private']

    DISPLAY_NAME = 'Clone Git Repository'
    CATEGORY = 'repository'
    DESCRIPTION = 'Clones Git repositories with support for SSH, branches, and submodules'

    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clone Git repository.

        Args:
            parameters: {
                'repo_url': Repository URL (HTTPS or SSH),
                'destination_path': Where to clone the repo,
                'branch': Optional branch to checkout,
                'depth': Optional shallow clone depth,
                'use_ssh': Whether to use SSH authentication (default: False),
                'recursive': Clone submodules recursively (default: False)
            }

        Returns:
            Dict with success status, clone path, and commit info
        """
        # Substitute variables
        params = self.substitute_variables(parameters)

        # Backward compatibility: support both old and new parameter names
        repo_url = params.get('repo_url') or params.get('url')
        destination = params.get('destination_path') or params.get('path')

        # Validate required parameters
        if not repo_url:
            raise ValueError("Missing required parameter: 'repo_url' (or legacy 'url')")
        if not destination:
            raise ValueError("Missing required parameter: 'destination_path' (or legacy 'path')")
        branch = params.get('branch')
        depth = params.get('depth')
        use_ssh = params.get('use_ssh', False)
        recursive = params.get('recursive', False)
        is_private = params.get('is_private', False)

        # Private repository validation and SSH key check
        if is_private:
            # Check if SSH key exists
            ssh_key_path = f"{self.home_directory}/.ssh/id_ed25519"
            if not os.path.exists(ssh_key_path):
                # Also check for RSA key as fallback
                ssh_key_path_rsa = f"{self.home_directory}/.ssh/id_rsa"
                if not os.path.exists(ssh_key_path_rsa):
                    raise ValueError(
                        f"Private repository requires SSH key, but no key found at {ssh_key_path} or {ssh_key_path_rsa}. "
                        "Please add 'Generate SSH Key' action before this clone action."
                    )
                ssh_key_path = ssh_key_path_rsa

            self.log_info(f"Private repository detected, SSH key verified at {ssh_key_path}")

            # Auto-convert HTTPS URLs to SSH format for private repos
            if repo_url.startswith('https://github.com/'):
                repo_url = repo_url.replace('https://github.com/', 'git@github.com:')
                if not repo_url.endswith('.git'):
                    repo_url = repo_url + '.git'
                self.log_info(f"Converted HTTPS URL to SSH format: {repo_url}")
            elif repo_url.startswith('https://gitlab.com/'):
                repo_url = repo_url.replace('https://gitlab.com/', 'git@gitlab.com:')
                if not repo_url.endswith('.git'):
                    repo_url = repo_url + '.git'
                self.log_info(f"Converted HTTPS URL to SSH format: {repo_url}")

        self.log_info(f"Cloning repository: {repo_url} → {destination}")

        # Validate destination doesn't exist
        if os.path.exists(destination):
            raise ValueError(f"Destination already exists: {destination}")

        # Build git clone command
        cmd = ['/usr/bin/git', 'clone']

        # Add branch if specified
        if branch:
            cmd.extend(['--branch', branch])

        # Add depth for shallow clone
        if depth:
            cmd.extend(['--depth', str(depth)])

        # Add recursive for submodules
        if recursive:
            cmd.append('--recursive')

        # Add repo URL and destination
        cmd.extend([repo_url, destination])

        try:
            # Execute git clone
            # Set up environment for SSH with StrictHostKeyChecking=no
            git_env = os.environ.copy()
            
            # Use ssh_key_path from parameters if provided for SSH authentication
            ssh_key_path = params.get('ssh_key_path')
            if ssh_key_path and os.path.exists(ssh_key_path):
                git_env['GIT_SSH_COMMAND'] = f'ssh -i {ssh_key_path} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
                self.log_info(f"Using SSH key: {ssh_key_path}")
            else:
                git_env['GIT_SSH_COMMAND'] = 'ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
                self.log_info("Using default SSH configuration")
            
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                cwd=os.path.dirname(destination) or '/',
                env=git_env
            )
            self.log_info(f"Repository cloned successfully")

            # Get current commit hash and branch
            commit_hash = subprocess.run(
                ['/usr/bin/git', 'rev-parse', 'HEAD'],
                capture_output=True,
                text=True,
                cwd=destination,
                check=True
            ).stdout.strip()

            current_branch = subprocess.run(
                ['/usr/bin/git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                capture_output=True,
                text=True,
                cwd=destination,
                check=True
            ).stdout.strip()

            self.log_info(f"Cloned at commit {commit_hash[:8]} on branch {current_branch}")

            return {
                'success': True,
                'repo_path': destination,
                'commit_hash': commit_hash,
                'branch': current_branch,
                'repo_url': repo_url
            }

        except subprocess.CalledProcessError as e:
            error_msg = f"Git clone failed: {e.stderr}"
            self.log_error(error_msg)

            # Clean up partial clone if it exists
            if os.path.exists(destination):
                shutil.rmtree(destination)
                self.log_info(f"Cleaned up partial clone: {destination}")

            raise Exception(error_msg)

    def validate(self, parameters: Dict[str, Any]) -> bool:
        """Validate Git clone parameters"""
        # Validate required parameters
        self.validate_parameters(parameters)

        # Validate repo URL format
        repo_url = parameters['repo_url']
        if not (repo_url.startswith('https://') or
                repo_url.startswith('git@') or
                repo_url.startswith('ssh://')):
            raise ValueError(f"Invalid repo URL format: {repo_url}")

        # Validate destination path
        destination = parameters['destination_path']
        if not destination:
            raise ValueError("Destination path cannot be empty")

        # Check if Git is available
        try:
            subprocess.run(['git', '--version'],
                         capture_output=True,
                         check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise ValueError("Git is not installed or not available in PATH")

        return True

    def rollback(self, parameters: Dict[str, Any], execution_result: Dict[str, Any]) -> bool:
        """Delete cloned repository"""
        if not execution_result.get('success'):
            return True  # Nothing to rollback

        try:
            repo_path = execution_result.get('repo_path')

            if repo_path and os.path.exists(repo_path):
                shutil.rmtree(repo_path)
                self.log_info(f"Deleted cloned repository: {repo_path}")

            return True

        except Exception as e:
            self.log_error(f"Rollback failed: {e}")
            return False
