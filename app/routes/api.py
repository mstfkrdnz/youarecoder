"""
API routes for workspace management.
"""
import subprocess
from flask import Blueprint, jsonify, current_app
from flask_login import login_required, current_user
from app.models import Workspace
from app.services.workspace_provisioner import WorkspaceProvisioner

bp = Blueprint('api', __name__, url_prefix='/api')


@bp.route('/workspace/<int:workspace_id>/status', methods=['GET'])
@login_required
def workspace_status(workspace_id):
    """Get workspace status including service health."""
    workspace = Workspace.query.get_or_404(workspace_id)

    # Check access
    if workspace.company_id != current_user.company_id:
        return jsonify({'error': 'Permission denied'}), 403

    # Check systemd service status
    try:
        result = subprocess.run([
            'systemctl', 'is-active', f'code-server@{workspace.linux_username}.service'
        ], capture_output=True, text=True, timeout=5)

        service_status = result.stdout.strip()
        service_active = (service_status == 'active')

    except Exception as e:
        current_app.logger.error(f"Error checking service status: {str(e)}")
        service_status = 'unknown'
        service_active = False

    return jsonify({
        'workspace_id': workspace.id,
        'name': workspace.name,
        'status': workspace.status,
        'service_status': service_status,
        'service_active': service_active,
        'port': workspace.port,
        'subdomain': workspace.subdomain,
        'url': workspace.get_url(),
        'disk_quota_gb': workspace.disk_quota_gb
    })


@bp.route('/workspace/<int:workspace_id>/restart', methods=['POST'])
@login_required
def restart_workspace(workspace_id):
    """Restart workspace code-server service."""
    workspace = Workspace.query.get_or_404(workspace_id)

    # Check ownership or admin
    if workspace.owner_id != current_user.id and not current_user.is_admin():
        return jsonify({'error': 'Permission denied'}), 403

    try:
        # Restart systemd service
        subprocess.run([
            'systemctl', 'restart', f'code-server@{workspace.linux_username}.service'
        ], check=True, capture_output=True, text=True, timeout=10)

        current_app.logger.info(f"Workspace restarted: {workspace_id}")

        return jsonify({
            'success': True,
            'message': f'Workspace "{workspace.name}" restarted successfully'
        })

    except subprocess.CalledProcessError as e:
        current_app.logger.error(f"Error restarting workspace: {e.stderr}")
        return jsonify({
            'success': False,
            'error': f'Failed to restart workspace: {e.stderr}'
        }), 500
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Restart command timed out'
        }), 500


@bp.route('/workspace/<int:workspace_id>/stop', methods=['POST'])
@login_required
def stop_workspace(workspace_id):
    """Stop workspace code-server service."""
    workspace = Workspace.query.get_or_404(workspace_id)

    # Check ownership or admin
    if workspace.owner_id != current_user.id and not current_user.is_admin():
        return jsonify({'error': 'Permission denied'}), 403

    try:
        # Stop systemd service
        subprocess.run([
            'systemctl', 'stop', f'code-server@{workspace.linux_username}.service'
        ], check=True, capture_output=True, text=True, timeout=10)

        current_app.logger.info(f"Workspace stopped: {workspace_id}")

        return jsonify({
            'success': True,
            'message': f'Workspace "{workspace.name}" stopped successfully'
        })

    except subprocess.CalledProcessError as e:
        current_app.logger.error(f"Error stopping workspace: {e.stderr}")
        return jsonify({
            'success': False,
            'error': f'Failed to stop workspace: {e.stderr}'
        }), 500


@bp.route('/workspace/<int:workspace_id>/start', methods=['POST'])
@login_required
def start_workspace(workspace_id):
    """Start workspace code-server service."""
    workspace = Workspace.query.get_or_404(workspace_id)

    # Check ownership or admin
    if workspace.owner_id != current_user.id and not current_user.is_admin():
        return jsonify({'error': 'Permission denied'}), 403

    try:
        # Start systemd service
        subprocess.run([
            'systemctl', 'start', f'code-server@{workspace.linux_username}.service'
        ], check=True, capture_output=True, text=True, timeout=10)

        current_app.logger.info(f"Workspace started: {workspace_id}")

        return jsonify({
            'success': True,
            'message': f'Workspace "{workspace.name}" started successfully'
        })

    except subprocess.CalledProcessError as e:
        current_app.logger.error(f"Error starting workspace: {e.stderr}")
        return jsonify({
            'success': False,
            'error': f'Failed to start workspace: {e.stderr}'
        }), 500


@bp.route('/workspace/<int:workspace_id>/logs', methods=['GET'])
@login_required
def workspace_logs(workspace_id):
    """Get recent logs from workspace service."""
    workspace = Workspace.query.get_or_404(workspace_id)

    # Check access
    if workspace.company_id != current_user.company_id:
        return jsonify({'error': 'Permission denied'}), 403

    try:
        # Get last 100 lines of systemd service logs
        result = subprocess.run([
            'journalctl', '-u', f'code-server@{workspace.linux_username}.service',
            '-n', '100', '--no-pager'
        ], capture_output=True, text=True, timeout=10)

        return jsonify({
            'success': True,
            'logs': result.stdout,
            'workspace_id': workspace.id
        })

    except subprocess.CalledProcessError as e:
        return jsonify({
            'success': False,
            'error': f'Failed to retrieve logs: {e.stderr}'
        }), 500
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Log retrieval timed out'
        }), 500
