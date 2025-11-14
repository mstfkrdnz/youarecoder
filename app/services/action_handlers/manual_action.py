"""
Manual Action Handler
Pauses provisioning and waits for user to complete a manual step
"""
from typing import Dict, Any
from app.services.action_handlers.base import BaseActionHandler
import subprocess


class ManualActionHandler(BaseActionHandler):
    """
    Handler for manual actions that require user intervention.

    The action pauses provisioning and displays instructions to the user.
    User must complete the manual step and click "Complete" to continue.

    Optional verification command can be executed to validate the manual step.
    """

    REQUIRED_PARAMETERS = ['instructions']
    OPTIONAL_PARAMETERS = [
        'verification_command',
        'timeout_seconds',
        'allow_skip'
    ]

    DISPLAY_NAME = 'Manual Action'
    CATEGORY = 'manual'
    DESCRIPTION = 'Pauses provisioning for user to complete manual step'

    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute manual action by storing instructions and waiting for completion.

        In mock mode, this just returns success with instructions.
        In real mode, provisioning would pause here and wait for user confirmation.

        Args:
            parameters: {
                'instructions': str - Instructions for the user (supports markdown),
                'verification_command': str (optional) - Shell command to verify completion,
                'timeout_seconds': int (optional) - Max time to wait for user,
                'allow_skip': bool (optional) - Whether user can skip this step
            }

        Returns:
            Dict with manual action status and instructions
        """
        params = self.substitute_variables(parameters)

        instructions = params.get('instructions', '')
        verification_cmd = params.get('verification_command')
        timeout = params.get('timeout_seconds', 600)  # Default 10 minutes
        allow_skip = params.get('allow_skip', False)

        self.log_info(f"Manual action required - waiting for user completion")
        self.log_info(f"Instructions: {instructions[:100]}...")

        result = {
            'success': True,
            'manual_action_required': True,
            'instructions': instructions,
            'timeout_seconds': timeout,
            'allow_skip': allow_skip,
            'verified': False
        }

        # In mock mode, we don't actually pause - just return the instructions
        # In real provisioning, the frontend would display these instructions
        # and wait for user to click "Complete"

        # If verification command is provided, we can optionally run it
        # (in real mode, this would run after user clicks "Complete")
        if verification_cmd and not self.mock_mode:
            try:
                # Substitute variables in verification command
                verification_cmd = self.substitute_variables({'cmd': verification_cmd})['cmd']

                self.log_info(f"Running verification command: {verification_cmd}")

                # Run verification command
                process = subprocess.run(
                    verification_cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=self.home_directory
                )

                if process.returncode == 0:
                    result['verified'] = True
                    result['verification_output'] = process.stdout
                    self.log_info("✅ Manual action verified successfully")
                else:
                    result['verified'] = False
                    result['verification_error'] = process.stderr
                    self.log_warning(f"⚠️ Verification failed: {process.stderr}")

                    # If verification fails and skip not allowed, mark as failed
                    if not allow_skip:
                        result['success'] = False
                        result['error'] = f"Manual action verification failed: {process.stderr}"

            except subprocess.TimeoutExpired:
                self.log_warning("Verification command timed out")
                result['verification_error'] = "Verification timed out"
                if not allow_skip:
                    result['success'] = False
                    result['error'] = "Manual action verification timed out"

            except Exception as e:
                self.log_warning(f"Verification command failed: {str(e)}")
                result['verification_error'] = str(e)
                if not allow_skip:
                    result['success'] = False
                    result['error'] = f"Manual action verification error: {str(e)}"

        return result

    def validate(self, parameters: Dict[str, Any]) -> bool:
        """
        Validate manual action parameters.

        Args:
            parameters: Parameters to validate

        Returns:
            True if valid, False otherwise
        """
        # Check required parameters
        if 'instructions' not in parameters:
            self.log_error("Missing required parameter: instructions")
            return False

        # Validate instructions is not empty
        if not parameters['instructions'] or not parameters['instructions'].strip():
            self.log_error("Instructions cannot be empty")
            return False

        # Validate timeout if provided
        if 'timeout_seconds' in parameters:
            timeout = parameters['timeout_seconds']
            if not isinstance(timeout, int) or timeout <= 0:
                self.log_error("timeout_seconds must be a positive integer")
                return False

        return True

    def rollback(self, parameters: Dict[str, Any], execution_result: Dict[str, Any]) -> bool:
        """
        No rollback needed for manual action.
        Manual actions don't modify system state directly.

        Args:
            parameters: Original parameters
            execution_result: Result from execute()

        Returns:
            True (always succeeds)
        """
        self.log_info("Manual action rollback - no action needed")
        return True
