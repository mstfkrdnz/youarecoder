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
    OPTIONAL_PARAMETERS = ['branch', 'depth', 'use_ssh', 'recursive']

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

        repo_url = params['repo_url']
        destination = params['destination_path']
        branch = params.get('branch')
        depth = params.get('depth')
        use_ssh = params.get('use_ssh', False)
        recursive = params.get('recursive', False)

        self.log_info(f"Cloning repository: {repo_url} → {destination}")

        # Validate destination doesn't exist
        if os.path.exists(destination):
            raise ValueError(f"Destination already exists: {destination}")

        # Build git clone command
        cmd = ['git', 'clone']

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
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                cwd=os.path.dirname(destination) or '/'
            )
            self.log_info(f"Repository cloned successfully")

            # Get current commit hash and branch
            commit_hash = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                capture_output=True,
                text=True,
                cwd=destination,
                check=True
            ).stdout.strip()

            current_branch = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
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
