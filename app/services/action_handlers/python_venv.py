"""
Python Virtual Environment Handler
Creates Python virtual environments
"""
import os
import subprocess
from typing import Dict, Any
from app.services.action_handlers.base import BaseActionHandler


class PythonVenvActionHandler(BaseActionHandler):
    """Create Python virtual environment"""

    REQUIRED_PARAMETERS = ['venv_path']
    OPTIONAL_PARAMETERS = ['python_version', 'system_site_packages']

    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create Python virtual environment.

        Args:
            parameters: {
                'venv_path': Path where venv will be created,
                'python_version': Python version (default: python3),
                'system_site_packages': Allow access to system packages (default: False)
            }

        Returns:
            Dict with venv path and Python version
        """
        params = self.substitute_variables(parameters)

        venv_path = params['venv_path']
        python_cmd = params.get('python_version', 'python3')
        system_site_packages = params.get('system_site_packages', False)

        self.log_info(f"Creating Python venv at {venv_path}")

        # Check if venv already exists
        if os.path.exists(venv_path):
            raise ValueError(f"Virtual environment already exists: {venv_path}")

        try:
            # Build venv command
            cmd = [python_cmd, '-m', 'venv']

            if system_site_packages:
                cmd.append('--system-site-packages')

            cmd.append(venv_path)

            # Create venv
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=120
            )

            self.log_info(f"Virtual environment created at {venv_path}")

            # Get Python version in venv
            python_version_result = subprocess.run([
                f'{venv_path}/bin/python', '--version'
            ], capture_output=True, text=True, check=True)

            python_version = python_version_result.stdout.strip()

            return {
                'success': True,
                'venv_path': venv_path,
                'python_version': python_version,
                'bin_path': f'{venv_path}/bin',
                'activate_script': f'{venv_path}/bin/activate'
            }

        except subprocess.CalledProcessError as e:
            error_msg = f"Virtual environment creation failed: {e.stderr}"
            self.log_error(error_msg)
            raise Exception(error_msg)

    def validate(self, parameters: Dict[str, Any]) -> bool:
        """Validate venv creation parameters"""
        self.validate_parameters(parameters)

        venv_path = parameters['venv_path']
        if not venv_path:
            raise ValueError("venv_path cannot be empty")

        # Check if Python is available
        python_cmd = parameters.get('python_version', 'python3')
        try:
            subprocess.run([python_cmd, '--version'],
                         check=True,
                         capture_output=True)
        except subprocess.CalledProcessError:
            raise ValueError(f"Python command not found: {python_cmd}")

        return True

    def rollback(self, parameters: Dict[str, Any], execution_result: Dict[str, Any]) -> bool:
        """Delete created virtual environment"""
        if not execution_result.get('success'):
            return True

        try:
            venv_path = execution_result.get('venv_path')

            if venv_path and os.path.exists(venv_path):
                import shutil
                shutil.rmtree(venv_path)
                self.log_info(f"Deleted virtual environment: {venv_path}")

            return True

        except Exception as e:
            self.log_error(f"Rollback failed: {e}")
            return False
