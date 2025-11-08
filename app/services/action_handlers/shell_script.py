"""
Shell Script Execution Action Handler
Executes shell commands and scripts
"""
import subprocess
import os
from typing import Dict, Any
from app.services.action_handlers.base import BaseActionHandler


class ShellScriptActionHandler(BaseActionHandler):
    """Execute shell commands and scripts"""

    REQUIRED_PARAMETERS = []
    OPTIONAL_PARAMETERS = ['command', 'script_path', 'script_content', 'working_directory', 'timeout', 'shell']

    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute shell script or command.

        Args:
            parameters: {
                'command': Direct command to execute (optional),
                'script_path': Path to script file (optional),
                'script_content': Script content to execute (optional),
                'working_directory': Optional working directory,
                'timeout': Optional timeout in seconds (default: 300),
                'shell': Shell to use (default: /bin/bash)
            }

        Returns:
            Dict with execution results
        """
        params = self.substitute_variables(parameters)

        command = params.get('command')
        script_path = params.get('script_path')
        script_content = params.get('script_content')
        working_dir = params.get('working_directory', self.home_directory)
        timeout = params.get('timeout', 300)
        shell = params.get('shell', '/bin/bash')

        self.log_info(f"Executing shell script (timeout: {timeout}s)")

        temp_script_path = None

        try:
            # Determine execution method
            if command:
                # Direct command execution
                self.log_info(f"Executing command: {command}")
                cmd = [shell, '-c', command]

            elif script_path:
                # Execute existing script
                script_path = self.substitute_variables({'path': script_path})['path']

                if not os.path.exists(script_path):
                    raise FileNotFoundError(f"Script file not found: {script_path}")

                self.log_info(f"Executing script: {script_path}")
                cmd = [shell, script_path]

            elif script_content:
                # Write content to temp script and execute
                import tempfile
                fd, temp_script_path = tempfile.mkstemp(suffix='.sh', prefix='workspace_script_')
                os.write(fd, script_content.encode('utf-8'))
                os.close(fd)
                os.chmod(temp_script_path, 0o755)

                self.log_info(f"Executing script content (temp: {temp_script_path})")
                cmd = [shell, temp_script_path]

            else:
                raise ValueError("Must specify one of: command, script_path, or script_content")

            # Execute
            result = subprocess.run(
                cmd,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False  # Don't raise on non-zero exit, we'll handle it
            )

            # Clean up temp script
            if temp_script_path and os.path.exists(temp_script_path):
                os.remove(temp_script_path)
                temp_script_path = None

            success = result.returncode == 0

            if success:
                self.log_info(f"Script executed successfully (exit code: 0)")
            else:
                self.log_warning(f"Script exited with code: {result.returncode}")

            return {
                'success': success,
                'exit_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'working_directory': working_dir,
                'timeout': timeout
            }

        except subprocess.TimeoutExpired as e:
            error_msg = f"Script execution timed out after {timeout}s"
            self.log_error(error_msg)

            # Clean up temp script
            if temp_script_path and os.path.exists(temp_script_path):
                os.remove(temp_script_path)

            raise Exception(error_msg)

        except Exception as e:
            # Clean up temp script
            if temp_script_path and os.path.exists(temp_script_path):
                os.remove(temp_script_path)

            error_msg = f"Script execution failed: {str(e)}"
            self.log_error(error_msg)
            raise Exception(error_msg)

    def validate(self, parameters: Dict[str, Any]) -> bool:
        """Validate shell script parameters"""
        command = parameters.get('command')
        script_path = parameters.get('script_path')
        script_content = parameters.get('script_content')

        # Must have at least one execution method
        if not (command or script_path or script_content):
            raise ValueError("Must specify one of: command, script_path, or script_content")

        # Can't have multiple execution methods
        methods_specified = sum([
            bool(command),
            bool(script_path),
            bool(script_content)
        ])

        if methods_specified > 1:
            raise ValueError("Can only specify one of: command, script_path, or script_content")

        # Validate timeout
        timeout = parameters.get('timeout', 300)
        if timeout <= 0:
            raise ValueError("Timeout must be positive")

        return True

    def rollback(self, parameters: Dict[str, Any], execution_result: Dict[str, Any]) -> bool:
        """
        No automatic rollback for shell scripts.
        Script authors should implement their own rollback logic if needed.
        """
        self.log_info("No automatic rollback for shell script execution")
        return True
