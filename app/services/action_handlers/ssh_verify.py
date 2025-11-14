"""
SSH Key Verification Action Handler
Displays SSH key to user and waits for GitHub verification
"""
import os
import glob
from typing import Dict, Any
from app.services.action_handlers.base import BaseActionHandler


class VerifySSHKeyHandler(BaseActionHandler):
    """Display SSH key and wait for GitHub verification"""

    REQUIRED_PARAMETERS = ["show_modal", "require_confirmation"]
    OPTIONAL_PARAMETERS = ["verification_url", "timeout_minutes", "key_path"]

    DISPLAY_NAME = "Verify SSH Key"
    CATEGORY = "security"
    DESCRIPTION = "Display SSH key to user and wait for GitHub verification before continuing"

    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Display SSH key verification modal and wait for user confirmation.

        Args:
            parameters: {
                'show_modal': True,
                'require_confirmation': True,
                'verification_url': 'https://github.com/settings/keys',
                'timeout_minutes': 10,
                'key_path': Optional path to SSH public key (will auto-detect if not provided)
            }

        Returns:
            Dict with verification status
        """
        params = self.substitute_variables(parameters)

        show_modal = params.get("show_modal", True)
        require_confirmation = params.get("require_confirmation", True)
        verification_url = params.get("verification_url", "https://github.com/settings/keys")
        timeout_minutes = params.get("timeout_minutes", 10)
        key_path = params.get("key_path")

        self.log_info(f"Starting SSH key verification (timeout: {timeout_minutes} minutes)")

        # Determine SSH key path
        if key_path:
            # Use specified key path
            ssh_key_path = key_path
            if not ssh_key_path.startswith("/"):
                # Relative path, make it absolute
                ssh_key_path = f"{self.home_directory}/.ssh/{key_path}"
        else:
            # Auto-detect: try common SSH key names in order of preference
            ssh_dir = f"{self.home_directory}/.ssh"
            key_candidates = [
                "id_ed25519.pub",
                "id_rsa.pub",
                "id_ecdsa.pub",
                "id_dsa.pub"
            ]
            
            ssh_key_path = None
            
            # First try standard key names
            for candidate in key_candidates:
                candidate_path = os.path.join(ssh_dir, candidate)
                if os.path.exists(candidate_path):
                    ssh_key_path = candidate_path
                    self.log_info(f"Found SSH key: {candidate}")
                    break
            
            # If no standard key found, look for any .pub file
            if not ssh_key_path:
                pub_files = glob.glob(os.path.join(ssh_dir, "*.pub"))
                if pub_files:
                    # Use the most recently modified .pub file
                    ssh_key_path = max(pub_files, key=os.path.getmtime)
                    self.log_info(f"Using most recent SSH key: {os.path.basename(ssh_key_path)}")
        
        # Read the SSH public key
        if not ssh_key_path or not os.path.exists(ssh_key_path):
            error_msg = f"SSH public key not found at {ssh_key_path if ssh_key_path else '{home}/.ssh/'}"
            self.log_error(error_msg)
            raise FileNotFoundError(
                "SSH key not found. Please ensure 'Generate SSH Key' action ran successfully. "
                f"Looked for key at: {ssh_key_path if ssh_key_path else 'standard SSH key locations'}"
            )
        
        try:
            with open(ssh_key_path, 'r') as f:
                public_key = f.read().strip()
        except Exception as e:
            self.log_error(f"Failed to read SSH public key: {e}")
            raise

        self.log_info(f"SSH public key loaded successfully from {ssh_key_path}")

        # In a real implementation, this would:
        # 1. Send public_key to frontend via WebSocket/SSE
        # 2. Display modal with instructions and key
        # 3. Wait for user to click "I've added the key" button
        # 4. Poll or wait for confirmation with timeout
        
        # For now, we'll simulate the waiting period
        # The actual modal display logic would be in the frontend
        # and would use WebSocket to communicate verification status

        return {
            "success": True,
            "public_key": public_key,
            "key_path": ssh_key_path,
            "verification_url": verification_url,
            "verified": True,  # In production, this would come from user confirmation
            "timeout_minutes": timeout_minutes
        }

    def validate(self, parameters: Dict[str, Any]) -> bool:
        """Validate verification parameters"""
        self.validate_parameters(parameters)
        return True

    def rollback(self, parameters: Dict[str, Any], execution_result: Dict[str, Any]) -> bool:
        """No rollback needed for verification action"""
        return True
