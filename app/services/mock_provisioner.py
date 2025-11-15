"""Mock provisioner for development environment."""
import logging
import secrets
import string
import time
import random
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
        """Simulate workspace provisioning with realistic delays."""
        from app import db

        logger.info(f"[MOCK] Provisioning workspace: {workspace.name}")
        logger.info(f"[MOCK] Would create user: {workspace.subdomain}")
        logger.info(f"[MOCK] Would allocate port: {workspace.port}")

        # Define provisioning steps with realistic durations (in seconds)
        steps = [
            ("Generate SSH Key", 2, 3),
            ("Add SSH Key to GitHub", 3, 5),
            ("Install System Packages", 4, 7),
            ("Clone Odoo Community", 5, 7),
            ("Clone Odoo Enterprise", 4, 6),
            ("Clone Development Tools", 3, 5),
            ("Create Custom Modules Directory", 2, 3),
            ("Create Odoo Data Directory", 2, 3),
            ("Create Python Virtual Environment", 3, 5),
            ("Install Odoo Community Requirements", 5, 7),
            ("Install Dev Tools Requirements", 4, 6),
            ("Create PostgreSQL Database", 3, 5),
            ("Create Odoo Configuration File", 2, 3),
            ("Create VS Code Workspace File", 2, 3),
            ("Install VS Code Extensions", 3, 4),
            ("Set Environment Variables", 2, 3),
            ("Initialize Odoo Database", 5, 7),
            ("Create Odoo Systemd Service", 2, 3),
            ("Display Completion Message", 2, 2),
        ]

        total_steps = len(steps)
        workspace.total_steps = total_steps
        workspace.provisioning_step = 0
        db.session.commit()

        # Execute each step with delay
        for idx, (step_name, min_delay, max_delay) in enumerate(steps, 1):
            # Random delay between min and max
            delay = random.uniform(min_delay, max_delay)

            logger.info(f"[MOCK] Step {idx}/{total_steps}: {step_name} (sleeping {delay:.1f}s)")
            time.sleep(delay)

            # Update progress
            workspace.provisioning_step = idx
            workspace.progress_percent = int((idx / total_steps) * 100)
            workspace.progress_message = f"Completed: {step_name}"
            db.session.commit()

            logger.info(f"[MOCK] Completed step {idx}/{total_steps}: {step_name}")

        # Final success state
        workspace.status = 'active'
        workspace.provisioning_state = 'completed'
        workspace.progress_percent = 100
        workspace.progress_message = 'Mock provisioning completed successfully'
        db.session.commit()

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
