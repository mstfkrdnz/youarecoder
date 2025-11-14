"""Mock provisioner for development environment."""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class MockWorkspaceProvisioner:
    """Mock provisioner that simulates operations without executing them."""

    def provision_workspace(self, workspace):
        """Simulate workspace provisioning."""
        logger.info(f"[MOCK] Provisioning workspace: {workspace.name}")
        logger.info(f"[MOCK] Would create user: {workspace.subdomain}")
        logger.info(f"[MOCK] Would allocate port: {workspace.code_server_port}")

        # Simulate success
        workspace.provisioning_state = 'active'
        workspace.provisioned_at = datetime.utcnow()
        return True

    def deprovision_workspace(self, workspace):
        """Simulate workspace deprovisioning."""
        logger.info(f"[MOCK] Deprovisioning workspace: {workspace.name}")
        workspace.provisioning_state = 'deprovisioned'
        return True
