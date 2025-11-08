"""
System Packages Installation Handler
Installs system packages using apt-get
"""
import subprocess
from typing import Dict, Any, List
from app.services.action_handlers.base import BaseActionHandler


class SystemPackagesActionHandler(BaseActionHandler):
    """Install system packages via apt-get"""

    REQUIRED_PARAMETERS = ['packages']
    OPTIONAL_PARAMETERS = ['update_cache']

    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Install system packages using apt-get.

        Args:
            parameters: {
                'packages': List of package names to install,
                'update_cache': Whether to run apt-get update first (default: True)
            }

        Returns:
            Dict with installed packages list
        """
        params = self.substitute_variables(parameters)

        packages = params['packages']
        if isinstance(packages, str):
            packages = [packages]

        update_cache = params.get('update_cache', True)

        self.log_info(f"Installing {len(packages)} system packages")

        installed_packages = []

        try:
            # Update package cache if requested
            if update_cache:
                self.log_info("Updating apt cache")
                subprocess.run([
                    'apt-get', 'update'
                ], check=True, capture_output=True, text=True, timeout=120)

            # Install packages
            for package in packages:
                self.log_info(f"Installing package: {package}")

                result = subprocess.run([
                    'apt-get', 'install', '-y', package
                ], check=True, capture_output=True, text=True, timeout=300)

                installed_packages.append(package)
                self.log_info(f"Package installed: {package}")

            return {
                'success': True,
                'installed_packages': installed_packages,
                'package_count': len(installed_packages)
            }

        except subprocess.CalledProcessError as e:
            error_msg = f"Package installation failed: {e.stderr}"
            self.log_error(error_msg)
            raise Exception(error_msg)

    def validate(self, parameters: Dict[str, Any]) -> bool:
        """Validate package installation parameters"""
        self.validate_parameters(parameters)

        packages = parameters['packages']
        if isinstance(packages, str):
            packages = [packages]

        if not packages or len(packages) == 0:
            raise ValueError("Packages list cannot be empty")

        # Check if apt-get is available
        try:
            subprocess.run(['which', 'apt-get'],
                         check=True,
                         capture_output=True)
        except subprocess.CalledProcessError:
            raise ValueError("apt-get is not available on this system")

        return True

    def rollback(self, parameters: Dict[str, Any], execution_result: Dict[str, Any]) -> bool:
        """
        Rollback installed packages.
        Note: Be careful with system packages - only remove if safe.
        """
        if not execution_result.get('success'):
            return True

        try:
            installed_packages = execution_result.get('installed_packages', [])

            if not installed_packages:
                return True

            self.log_info(f"Rolling back {len(installed_packages)} packages")

            for package in installed_packages:
                try:
                    subprocess.run([
                        'apt-get', 'remove', '-y', package
                    ], check=True, capture_output=True, text=True, timeout=120)
                    self.log_info(f"Removed package: {package}")
                except subprocess.CalledProcessError as e:
                    self.log_warning(f"Could not remove {package}: {e.stderr}")
                    # Continue with other packages

            return True

        except Exception as e:
            self.log_error(f"Rollback failed: {e}")
            return False
