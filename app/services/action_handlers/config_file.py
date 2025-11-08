"""
Configuration File Action Handler
Writes configuration files with content and permissions
"""
import os
import json
from typing import Dict, Any
from app.services.action_handlers.base import BaseActionHandler


class ConfigFileActionHandler(BaseActionHandler):
    """Write configuration files with proper content and permissions"""

    REQUIRED_PARAMETERS = ['file_path', 'content']
    OPTIONAL_PARAMETERS = ['mode', 'format', 'backup_existing']

    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Write configuration file.

        Args:
            parameters: {
                'file_path': Path to config file,
                'content': File content (string or dict for JSON),
                'mode': Optional file permissions (default: 0o644),
                'format': Optional format: 'text', 'json' (default: 'text'),
                'backup_existing': Backup if exists (default: True)
            }

        Returns:
            Dict with success status and file info
        """
        params = self.substitute_variables(parameters)

        file_path = params['file_path']
        content = params['content']
        mode = params.get('mode', 0o644)
        file_format = params.get('format', 'text')
        backup_existing = params.get('backup_existing', True)

        # Convert mode if string
        if isinstance(mode, str):
            mode = int(mode, 8)

        self.log_info(f"Writing config file: {file_path} (format: {file_format})")

        backup_path = None
        file_existed = os.path.exists(file_path)

        try:
            # Backup existing file
            if file_existed and backup_existing:
                backup_path = f"{file_path}.backup"
                import shutil
                shutil.copy2(file_path, backup_path)
                self.log_info(f"Backed up existing file to: {backup_path}")

            # Create parent directory if needed
            parent_dir = os.path.dirname(file_path)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, mode=0o755, exist_ok=True)

            # Write content based on format
            if file_format == 'json':
                if isinstance(content, str):
                    content = json.loads(content)
                with open(file_path, 'w') as f:
                    json.dump(content, f, indent=2)
            else:
                with open(file_path, 'w') as f:
                    f.write(content)

            # Set permissions
            os.chmod(file_path, mode)

            self.log_info(f"Config file written successfully: {file_path}")

            return {
                'success': True,
                'file_path': file_path,
                'mode': oct(mode),
                'format': file_format,
                'file_existed': file_existed,
                'backup_path': backup_path,
                'size_bytes': os.path.getsize(file_path)
            }

        except Exception as e:
            # Restore backup on error
            if backup_path and os.path.exists(backup_path):
                import shutil
                shutil.copy2(backup_path, file_path)
                self.log_info(f"Restored backup after error")

            error_msg = f"Failed to write config file {file_path}: {str(e)}"
            self.log_error(error_msg)
            raise Exception(error_msg)

    def validate(self, parameters: Dict[str, Any]) -> bool:
        """Validate configuration file parameters"""
        self.validate_parameters(parameters)

        file_path = parameters['file_path']
        content = parameters['content']
        file_format = parameters.get('format', 'text')

        if not file_path:
            raise ValueError("File path cannot be empty")

        if content is None:
            raise ValueError("Content cannot be None")

        if file_format not in ['text', 'json']:
            raise ValueError(f"Invalid format: {file_format}. Must be 'text' or 'json'")

        # Validate JSON format if specified
        if file_format == 'json':
            if isinstance(content, str):
                try:
                    json.loads(content)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid JSON content: {e}")

        return True

    def rollback(self, parameters: Dict[str, Any], execution_result: Dict[str, Any]) -> bool:
        """Restore backup or delete created file"""
        if not execution_result.get('success'):
            return True

        try:
            file_path = execution_result.get('file_path')
            backup_path = execution_result.get('backup_path')
            file_existed = execution_result.get('file_existed', False)

            if backup_path and os.path.exists(backup_path):
                # Restore from backup
                import shutil
                shutil.copy2(backup_path, file_path)
                os.remove(backup_path)
                self.log_info(f"Restored file from backup: {file_path}")
            elif not file_existed and file_path and os.path.exists(file_path):
                # Delete newly created file
                os.remove(file_path)
                self.log_info(f"Deleted created file: {file_path}")

            return True

        except Exception as e:
            self.log_error(f"Rollback failed: {e}")
            return False
