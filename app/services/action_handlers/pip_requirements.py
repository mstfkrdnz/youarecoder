"""
Pip Requirements Installation Handler
Installs Python packages from requirements file or list
"""
import os
import subprocess
from typing import Dict, Any, List
from app.services.action_handlers.base import BaseActionHandler


class PipRequirementsActionHandler(BaseActionHandler):
    """Install Python packages via pip"""

    REQUIRED_PARAMETERS = []
    OPTIONAL_PARAMETERS = ['requirements_file', 'packages', 'venv_path', 'upgrade']

    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Install Python packages via pip.

        Args:
            parameters: {
                'requirements_file': Path to requirements.txt (optional),
                'packages': List of packages to install (optional),
                'venv_path': Virtual environment path (optional, uses system pip if not specified),
                'upgrade': Whether to upgrade packages (default: False)
            }

        Returns:
            Dict with installed packages info
        """
        params = self.substitute_variables(parameters)

        requirements_file = params.get('requirements_file')
        packages = params.get('packages', [])
        venv_path = params.get('venv_path')
        upgrade = params.get('upgrade', False)

        if isinstance(packages, str):
            packages = [packages]

        # Determine pip command
        if venv_path:
            pip_cmd = f'{venv_path}/bin/pip'
        else:
            pip_cmd = 'pip3'

        self.log_info(f"Installing Python packages using {pip_cmd}")

        installed_items = []

        try:
            # Install from requirements file
            if requirements_file:
                self.log_info(f"Installing from requirements file: {requirements_file}")

                # Substitute variables in requirements file path
                requirements_file = self.substitute_variables({'path': requirements_file})['path']

                if not os.path.exists(requirements_file):
                    raise FileNotFoundError(f"Requirements file not found: {requirements_file}")

                cmd = [pip_cmd, 'install', '-r', requirements_file]
                if upgrade:
                    cmd.append('--upgrade')

                subprocess.run(
                    cmd,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=600
                )

                installed_items.append(f"requirements:{requirements_file}")
                self.log_info(f"Installed packages from {requirements_file}")

            # Install individual packages
            if packages:
                self.log_info(f"Installing {len(packages)} packages")

                for package in packages:
                    cmd = [pip_cmd, 'install', package]
                    if upgrade:
                        cmd.append('--upgrade')

                    subprocess.run(
                        cmd,
                        check=True,
                        capture_output=True,
                        text=True,
                        timeout=300
                    )

                    installed_items.append(f"package:{package}")
                    self.log_info(f"Installed package: {package}")

            return {
                'success': True,
                'installed_items': installed_items,
                'install_count': len(installed_items),
                'pip_command': pip_cmd
            }

        except subprocess.CalledProcessError as e:
            error_msg = f"Pip installation failed: {e.stderr}"
            self.log_error(error_msg)
            raise Exception(error_msg)
        except FileNotFoundError as e:
            error_msg = str(e)
            self.log_error(error_msg)
            raise Exception(error_msg)

    def validate(self, parameters: Dict[str, Any]) -> bool:
        """Validate pip installation parameters"""
        requirements_file = parameters.get('requirements_file')
        packages = parameters.get('packages', [])

        if not requirements_file and not packages:
            raise ValueError("Either requirements_file or packages must be specified")

        # Check if pip is available
        venv_path = parameters.get('venv_path')
        if venv_path:
            pip_cmd = f'{venv_path}/bin/pip'
        else:
            pip_cmd = 'pip3'

        try:
            subprocess.run([pip_cmd, '--version'],
                         check=True,
                         capture_output=True)
        except subprocess.CalledProcessError:
            raise ValueError(f"Pip command not found: {pip_cmd}")

        return True

    def rollback(self, parameters: Dict[str, Any], execution_result: Dict[str, Any]) -> bool:
        """
        Rollback pip installations.
        Note: Uninstalling packages can be risky, only for development environments.
        """
        if not execution_result.get('success'):
            return True

        try:
            installed_items = execution_result.get('installed_items', [])
            pip_cmd = execution_result.get('pip_command', 'pip3')

            if not installed_items:
                return True

            self.log_info(f"Rolling back pip installations")

            for item in installed_items:
                item_type, item_value = item.split(':', 1)

                if item_type == 'package':
                    try:
                        subprocess.run([
                            pip_cmd, 'uninstall', '-y', item_value
                        ], check=True, capture_output=True, text=True, timeout=60)
                        self.log_info(f"Uninstalled package: {item_value}")
                    except subprocess.CalledProcessError as e:
                        self.log_warning(f"Could not uninstall {item_value}: {e.stderr}")

                # Note: Cannot easily rollback requirements file installations
                # as we don't track individual packages from it

            return True

        except Exception as e:
            self.log_error(f"Rollback failed: {e}")
            return False
