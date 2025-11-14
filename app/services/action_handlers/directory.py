"""
Directory Creation Action Handler
Creates directories with specified permissions
"""
import os
import shutil
from typing import Dict, Any
from app.services.action_handlers.base import BaseActionHandler


class DirectoryActionHandler(BaseActionHandler):
    """Create directories with proper permissions"""

    REQUIRED_PARAMETERS = ['path']
    OPTIONAL_PARAMETERS = ['mode', 'parents', 'exist_ok']

    DISPLAY_NAME = 'Create Directory'
    CATEGORY = 'filesystem'
    DESCRIPTION = 'Creates directories with specified permissions and parent directory support'

    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create directory with specified permissions.

        Args:
            parameters: {
                'path': Directory path to create,
                'mode': Optional permissions (default: 0o755),
                'parents': Create parent directories (default: True),
                'exist_ok': Don't error if exists (default: True)
            }

        Returns:
            Dict with success status and created path
        """
        params = self.substitute_variables(parameters)

        path = params['path']
        mode = params.get('mode', 0o755)
        parents = params.get('parents', True)
        exist_ok = params.get('exist_ok', True)

        # Convert mode if it's a string (e.g., "0o755")
        if isinstance(mode, str):
            mode = int(mode, 8)

        self.log_info(f"Creating directory: {path} (mode: {oct(mode)})")

        # Mock mode: simulate directory creation
        if self.mock_mode:
            self.log_info("MOCK MODE: Simulating directory creation")
            return {
                'success': True,
                'path': path,
                'mode': oct(mode),
                'exists': True,
                'is_directory': True,
                'mock': True
            }

        try:
            if parents:
                os.makedirs(path, mode=mode, exist_ok=exist_ok)
            else:
                os.mkdir(path, mode=mode)

            self.log_info(f"Directory created successfully: {path}")

            return {
                'success': True,
                'path': path,
                'mode': oct(mode),
                'exists': os.path.exists(path),
                'is_directory': os.path.isdir(path)
            }

        except FileExistsError as e:
            if not exist_ok:
                error_msg = f"Directory already exists: {path}"
                self.log_error(error_msg)
                raise Exception(error_msg)

            self.log_info(f"Directory already exists: {path}")
            return {
                'success': True,
                'path': path,
                'mode': oct(mode),
                'exists': True,
                'already_existed': True
            }

        except Exception as e:
            error_msg = f"Failed to create directory {path}: {str(e)}"
            self.log_error(error_msg)
            raise Exception(error_msg)

    def validate(self, parameters: Dict[str, Any]) -> bool:
        """Validate directory creation parameters"""
        # Validate required parameters
        self.validate_parameters(parameters)

        path = parameters['path']

        if not path:
            raise ValueError("Directory path cannot be empty")

        # Check parent directory exists if parents=False
        if not parameters.get('parents', True):
            parent_dir = os.path.dirname(path)
            if parent_dir and not os.path.exists(parent_dir):
                raise ValueError(f"Parent directory does not exist: {parent_dir}")

        return True

    def rollback(self, parameters: Dict[str, Any], execution_result: Dict[str, Any]) -> bool:
        """Delete created directory"""
        if not execution_result.get('success'):
            return True  # Nothing to rollback

        # Don't delete if directory already existed
        if execution_result.get('already_existed'):
            self.log_info("Directory already existed, not deleting")
            return True

        try:
            path = execution_result.get('path')

            if path and os.path.exists(path):
                # Only delete if directory is empty
                if os.path.isdir(path) and not os.listdir(path):
                    os.rmdir(path)
                    self.log_info(f"Deleted empty directory: {path}")
                else:
                    self.log_warning(f"Directory not empty, skipping deletion: {path}")

            return True

        except Exception as e:
            self.log_error(f"Rollback failed: {e}")
            return False
