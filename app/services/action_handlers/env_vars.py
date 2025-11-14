"""
Environment Variables Action Handler
Sets environment variables in shell config files
"""
import os
from typing import Dict, Any
from app.services.action_handlers.base import BaseActionHandler


class EnvironmentVariablesActionHandler(BaseActionHandler):
    """Set environment variables in shell configuration"""

    REQUIRED_PARAMETERS = ['variables']
    OPTIONAL_PARAMETERS = ['shell_config_file', 'export_format']

    DISPLAY_NAME = 'Set Environment Variables'
    CATEGORY = 'environment'
    DESCRIPTION = 'Configures environment variables in shell configuration files'

    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Set environment variables.

        Args:
            parameters: {
                'variables': Dict of env var name → value,
                'shell_config_file': Optional config file (default: ~/.bashrc),
                'export_format': Whether to use export (default: True)
            }

        Returns:
            Dict with set variables info
        """
        params = self.substitute_variables(parameters)

        variables = params['variables']
        shell_config = params.get('shell_config_file', f'{self.home_directory}/.bashrc')
        use_export = params.get('export_format', True)

        # Substitute variables in shell_config path
        shell_config = self.substitute_variables({'path': shell_config})['path']

        self.log_info(f"Setting {len(variables)} environment variables in {shell_config}")

        backup_path = None
        set_variables = []

        try:
            # Backup existing config
            if os.path.exists(shell_config):
                backup_path = f"{shell_config}.backup"
                import shutil
                shutil.copy2(shell_config, backup_path)
                self.log_info(f"Backed up config to: {backup_path}")

            # Read existing content
            if os.path.exists(shell_config):
                with open(shell_config, 'r') as f:
                    existing_content = f.read()
            else:
                existing_content = ""
                # Create parent directory if needed
                parent_dir = os.path.dirname(shell_config)
                if parent_dir and not os.path.exists(parent_dir):
                    os.makedirs(parent_dir, mode=0o755, exist_ok=True)

            # Prepare variable lines
            var_lines = []
            var_lines.append("\n# Environment variables set by workspace provisioning")

            for var_name, var_value in variables.items():
                if use_export:
                    line = f'export {var_name}="{var_value}"'
                else:
                    line = f'{var_name}="{var_value}"'

                var_lines.append(line)
                set_variables.append(var_name)

            # Append to config file
            with open(shell_config, 'a') as f:
                f.write('\n'.join(var_lines) + '\n')

            self.log_info(f"Set {len(set_variables)} environment variables")

            return {
                'success': True,
                'shell_config_file': shell_config,
                'variables_set': set_variables,
                'variable_count': len(set_variables),
                'backup_path': backup_path,
                'use_export': use_export
            }

        except Exception as e:
            # Restore backup on error
            if backup_path and os.path.exists(backup_path):
                import shutil
                shutil.copy2(backup_path, shell_config)
                self.log_info(f"Restored backup after error")

            error_msg = f"Failed to set environment variables: {str(e)}"
            self.log_error(error_msg)
            raise Exception(error_msg)

    def validate(self, parameters: Dict[str, Any]) -> bool:
        """Validate environment variables parameters"""
        self.validate_parameters(parameters)

        variables = parameters['variables']

        if not variables:
            raise ValueError("Variables dict cannot be empty")

        if not isinstance(variables, dict):
            raise ValueError("Variables must be a dict")

        # Validate variable names (alphanumeric + underscore)
        for var_name in variables.keys():
            if not var_name.replace('_', '').isalnum():
                raise ValueError(f"Invalid variable name: {var_name}")

        return True

    def rollback(self, parameters: Dict[str, Any], execution_result: Dict[str, Any]) -> bool:
        """Restore backup config file"""
        if not execution_result.get('success'):
            return True

        try:
            shell_config = execution_result.get('shell_config_file')
            backup_path = execution_result.get('backup_path')

            if backup_path and os.path.exists(backup_path):
                # Restore from backup
                import shutil
                shutil.copy2(backup_path, shell_config)
                os.remove(backup_path)
                self.log_info(f"Restored config from backup: {shell_config}")

            return True

        except Exception as e:
            self.log_error(f"Rollback failed: {e}")
            return False
