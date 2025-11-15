"""Mock provisioner for development environment."""
import logging
import secrets
import string
from datetime import datetime

logger = logging.getLogger(__name__)

class MockWorkspaceProvisioner:
    """Mock provisioner that simulates operations without executing them."""

    def __init__(self):
        """Initialize mock provisioner with configuration."""
        self.port_range_start = 10000
        self.port_range_end = 20000

    def allocate_port(self) -> int:
        """Allocate next available port from the configured range."""
        from app.models import Workspace
        used_ports = {ws.port for ws in Workspace.query.all()}

        for port in range(self.port_range_start, self.port_range_end + 1):
            if port not in used_ports:
                logger.info(f"[MOCK] Allocated port: {port}")
                return port

        # Fallback to random port if all used
        port = self.port_range_start
        logger.info(f"[MOCK] Allocated fallback port: {port}")
        return port

    def generate_password(self, length: int = 18) -> str:
        """Generate secure random password."""
        alphabet = string.ascii_letters + string.digits
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        logger.info(f"[MOCK] Generated password (length: {length})")
        return password

    def provision_workspace(self, workspace):
        """Simulate workspace provisioning."""
        logger.info(f"[MOCK] Provisioning workspace: {workspace.name}")
        logger.info(f"[MOCK] Would create user: {workspace.subdomain}")
        logger.info(f"[MOCK] Would allocate port: {workspace.port}")

        # Simulate success - update status and provisioning state
        workspace.status = 'active'
        workspace.provisioning_state = 'completed'
        workspace.progress_percent = 100
        workspace.progress_message = 'Mock provisioning completed successfully'

        return {'success': True, 'message': 'Mock provisioning successful'}

    def deprovision_workspace(self, workspace):
        """Simulate workspace deprovisioning."""
        logger.info(f"[MOCK] Deprovisioning workspace: {workspace.name}")
        workspace.provisioning_state = 'deprovisioned'
        return {'success': True, 'message': 'Mock deprovisioning successful'}

    def start_workspace_service(self, workspace):
        """Simulate starting workspace service."""
        logger.info(f"[MOCK] Starting workspace service: {workspace.name}")
        return {'success': True, 'message': 'Mock service started'}

    def stop_workspace_service(self, workspace):
        """Simulate stopping workspace service."""
        logger.info(f"[MOCK] Stopping workspace service: {workspace.name}")
        return {'success': True, 'message': 'Mock service stopped'}

    def restart_workspace_service(self, workspace):
        """Simulate restarting workspace service."""
        logger.info(f"[MOCK] Restarting workspace service: {workspace.name}")
        return {'success': True, 'message': 'Mock service restarted'}

    def get_workspace_logs(self, workspace, lines=100, since=None):
        """Simulate getting workspace logs."""
        logger.info(f"[MOCK] Getting logs for workspace: {workspace.name}")
        return {
            'logs': ['[MOCK] Log line 1', '[MOCK] Log line 2', '[MOCK] Log line 3'],
            'truncated': False
        }

    def _verify_github_ssh(self, username: str) -> bool:
        """Simulate SSH verification."""
        logger.info(f"[MOCK] Verifying GitHub SSH for user: {username}")
        return True

    def resume_provisioning_after_ssh_verification(self, workspace, user_id: int):
        """Simulate resuming provisioning after SSH verification."""
        logger.info(f"[MOCK] Resuming provisioning for workspace: {workspace.name}")
        return {'success': True, 'message': 'Mock provisioning resumed'}
