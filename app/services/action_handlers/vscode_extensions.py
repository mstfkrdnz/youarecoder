"""
VS Code Extensions Action Handler
Installs VS Code extensions for workspace
"""
import subprocess
from typing import Dict, Any, List
from app.services.action_handlers.base import BaseActionHandler


class VSCodeExtensionsActionHandler(BaseActionHandler):
    """Install VS Code extensions"""

    REQUIRED_PARAMETERS = ['extensions']
    OPTIONAL_PARAMETERS = []

    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Install VS Code extensions.

        Args:
            parameters: {
                'extensions': List of extension IDs to install
            }

        Returns:
            Dict with installed extensions info
        """
        params = self.substitute_variables(parameters)

        extensions = params['extensions']
        if isinstance(extensions, str):
            extensions = [extensions]

        self.log_info(f"Installing {len(extensions)} VS Code extensions")

        installed_extensions = []
        failed_extensions = []

        for extension in extensions:
            self.log_info(f"Installing extension: {extension}")

            try:
                # Install extension using code-server CLI
                subprocess.run(
                    ['code-server', '--install-extension', extension],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=120
                )

                installed_extensions.append(extension)
                self.log_info(f"Installed extension: {extension}")

            except subprocess.CalledProcessError as e:
                self.log_warning(f"Failed to install extension {extension}: {e.stderr}")
                failed_extensions.append(extension)
            except subprocess.TimeoutExpired:
                self.log_warning(f"Timeout installing extension: {extension}")
                failed_extensions.append(extension)

        return {
            'success': len(failed_extensions) == 0,
            'installed_extensions': installed_extensions,
            'failed_extensions': failed_extensions,
            'total_requested': len(extensions),
            'installed_count': len(installed_extensions),
            'failed_count': len(failed_extensions)
        }

    def validate(self, parameters: Dict[str, Any]) -> bool:
        """Validate VS Code extensions parameters"""
        self.validate_parameters(parameters)

        extensions = parameters['extensions']

        if not extensions:
            raise ValueError("Extensions list cannot be empty")

        if isinstance(extensions, str):
            extensions = [extensions]

        if not isinstance(extensions, list):
            raise ValueError("Extensions must be a list or string")

        # Check if code-server is available
        try:
            subprocess.run(
                ['code-server', '--version'],
                check=True,
                capture_output=True,
                timeout=10
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise ValueError("code-server is not installed or not available in PATH")

        return True

    def rollback(self, parameters: Dict[str, Any], execution_result: Dict[str, Any]) -> bool:
        """Uninstall installed extensions"""
        if not execution_result.get('success') and not execution_result.get('installed_extensions'):
            return True

        try:
            installed_extensions = execution_result.get('installed_extensions', [])

            if not installed_extensions:
                return True

            self.log_info(f"Rolling back {len(installed_extensions)} extensions")

            for extension in installed_extensions:
                try:
                    subprocess.run(
                        ['code-server', '--uninstall-extension', extension],
                        check=True,
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                    self.log_info(f"Uninstalled extension: {extension}")
                except subprocess.CalledProcessError as e:
                    self.log_warning(f"Could not uninstall {extension}: {e.stderr}")

            return True

        except Exception as e:
            self.log_error(f"Rollback failed: {e}")
            return False
