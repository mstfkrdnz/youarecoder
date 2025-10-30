"""
Workspace routes (create, delete, manage).
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, make_response
from flask_login import login_required, current_user
from app import db
from app.models import Workspace, WorkspaceTemplate
from app.forms import WorkspaceForm
from app.services.workspace_provisioner import WorkspaceProvisioner, WorkspaceProvisionerError
from app.services.email_service import send_workspace_ready_email
from app.services.audit_logger import AuditLogger, WorkspaceSessionTracker
from app.utils.decorators import require_workspace_ownership

bp = Blueprint('workspace', __name__, url_prefix='/workspace')

@bp.route('/')
@login_required
def list():
    """List workspaces (admin sees all company workspaces, developer sees only own)."""
    if current_user.is_admin():
        workspaces = Workspace.query.filter_by(company_id=current_user.company_id).order_by(Workspace.created_at.desc()).all()
    else:
        workspaces = current_user.workspaces.order_by(Workspace.created_at.desc()).all()
    return render_template('workspace/list.html', workspaces=workspaces)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create new workspace route with full provisioning."""
    form = WorkspaceForm()

    # Populate template choices (official + company templates)
    official_templates = WorkspaceTemplate.query.filter_by(
        visibility='official',
        is_active=True
    ).all()

    company_templates = WorkspaceTemplate.query.filter_by(
        company_id=current_user.company_id,
        visibility='company',
        is_active=True
    ).all()

    # Build choices list: [(0, 'No Template')] + template options
    form.template_id.choices = [(0, 'No Template (Blank Workspace)')]
    form.template_id.choices += [(t.id, f"{t.name} ({t.category})") for t in official_templates]
    if company_templates:
        form.template_id.choices += [(t.id, f"{t.name} (Company)") for t in company_templates]

    if form.validate_on_submit():
        # Check user's personal workspace quota (Phase 2: Per-developer quota)
        user_workspace_count = current_user.workspaces.count()
        user_quota = getattr(current_user, 'workspace_quota', current_user.company.max_workspaces)

        if user_workspace_count >= user_quota:
            flash(f'You have reached your workspace quota ({user_quota}). Contact your administrator for more workspace capacity.', 'error')
            return redirect(url_for('main.dashboard'))

        # Also check company-wide limit (legacy fallback)
        if not current_user.company.can_create_workspace():
            flash('Company workspace limit reached for your plan', 'error')
            return redirect(url_for('main.dashboard'))

        # Initialize provisioner
        provisioner = WorkspaceProvisioner()

        try:
            # Allocate port
            port = provisioner.allocate_port()

            # Generate secure password for code-server
            code_server_password = provisioner.generate_password()

            # Create workspace record
            # Sanitize workspace name for Linux username (replace hyphens with underscores)
            sanitized_name = form.name.data.replace('-', '_')

            # Get template_id (0 means no template)
            template_id = form.template_id.data if form.template_id.data != 0 else None

            workspace = Workspace(
                name=form.name.data,
                subdomain=f"{current_user.company.subdomain}-{form.name.data}",
                linux_username=f"{current_user.company.subdomain}_{sanitized_name}",
                port=port,
                code_server_password=code_server_password,
                company_id=current_user.company.id,
                owner_id=current_user.id,
                template_id=template_id,
                status='pending',
                disk_quota_gb=current_user.company.plan == 'starter' and 10 or
                             (current_user.company.plan == 'team' and 50 or 250)
            )
            db.session.add(workspace)
            db.session.commit()

            # Provision workspace (Linux user, code-server, systemd service)
            result = provisioner.provision_workspace(workspace)

            if result['success']:
                # Audit log: workspace created successfully
                AuditLogger.log_workspace_create(workspace)

                # Send workspace ready email
                try:
                    send_workspace_ready_email(current_user, workspace)
                    current_app.logger.info(f"Workspace ready email sent for {workspace.id}")
                except Exception as e:
                    current_app.logger.error(f"Failed to send workspace email to {current_user.email}: {str(e)}")

                flash(f'Workspace "{form.name.data}" created and provisioned successfully! Check your email.', 'success')
                current_app.logger.info(f"Workspace created: {workspace.id} on port {port}")
            else:
                flash(f'Workspace created but provisioning incomplete', 'warning')

        except WorkspaceProvisionerError as e:
            current_app.logger.error(f"Workspace provisioning error: {str(e)}")
            flash(f'Error creating workspace: {str(e)}', 'error')
            
            return redirect(url_for("main.dashboard"))

        return redirect(url_for("main.dashboard"))

    # GET request - return full page template
    return render_template('workspace/create.html', form=form)

@bp.route('/<int:workspace_id>/delete', methods=['POST'])
@login_required
@require_workspace_ownership
def delete(workspace_id):
    """Delete workspace route with full deprovisioning."""
    workspace = Workspace.query.get_or_404(workspace_id)

    # Initialize provisioner
    provisioner = WorkspaceProvisioner()

    try:
        # Audit log: workspace deletion (log before delete for workspace data)
        AuditLogger.log_workspace_delete(workspace)

        # Deprovision workspace (stop service, remove user, cleanup)
        result = provisioner.deprovision_workspace(workspace)

        if result['success']:
            flash(f'Workspace "{workspace.name}" deleted successfully', 'success')
            current_app.logger.info(f"Workspace deprovisioned: {workspace_id}")
        else:
            flash(f'Workspace deletion incomplete', 'warning')

    except WorkspaceProvisionerError as e:
        current_app.logger.error(f"Workspace deprovisioning error: {str(e)}")
        flash(f'Error deleting workspace: {str(e)}', 'error')

    return redirect(url_for('main.dashboard'))

@bp.route('/<int:workspace_id>')
@login_required
@require_workspace_ownership
def view(workspace_id):
    """View workspace details route."""
    workspace = Workspace.query.get_or_404(workspace_id)
    return render_template('workspace/view.html', workspace=workspace)

@bp.route('/<int:workspace_id>/manage')
@login_required
@require_workspace_ownership
def manage(workspace_id):
    """Manage workspace modal - returns HTML fragment for HTMX."""
    workspace = Workspace.query.get_or_404(workspace_id)
    return render_template('workspace/manage_modal.html', workspace=workspace)

# Phase 4: Workspace Lifecycle Management Routes

@bp.route('/<int:workspace_id>/start', methods=['POST'])
@login_required
@require_workspace_ownership
def start(workspace_id):
    """Start workspace code-server service."""
    workspace = Workspace.query.get_or_404(workspace_id)

    if workspace.is_running:
        return jsonify({'error': 'Workspace is already running'}), 400

    provisioner = WorkspaceProvisioner()

    try:
        # Start code-server systemd service
        result = provisioner.start_workspace_service(workspace)

        if result['success']:
            # Update workspace status
            workspace.is_running = True
            workspace.last_started_at = db.func.now()
            workspace.status = 'running'
            db.session.commit()

            # Audit log
            AuditLogger.log_workspace_action(workspace, 'start', current_user.id)

            current_app.logger.info(f"Workspace {workspace_id} started by user {current_user.id}")
            return jsonify({'success': True, 'message': 'Workspace started successfully'}), 200
        else:
            return jsonify({'error': result.get('message', 'Failed to start workspace')}), 500

    except WorkspaceProvisionerError as e:
        current_app.logger.error(f"Error starting workspace {workspace_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:workspace_id>/stop', methods=['POST'])
@login_required
@require_workspace_ownership
def stop(workspace_id):
    """Stop workspace code-server service."""
    workspace = Workspace.query.get_or_404(workspace_id)

    if not workspace.is_running:
        return jsonify({'error': 'Workspace is not running'}), 400

    provisioner = WorkspaceProvisioner()

    try:
        # Stop code-server systemd service
        result = provisioner.stop_workspace_service(workspace)

        if result['success']:
            # Update workspace status
            workspace.is_running = False
            workspace.last_stopped_at = db.func.now()
            workspace.status = 'stopped'
            db.session.commit()

            # Audit log
            AuditLogger.log_workspace_action(workspace, 'stop', current_user.id)

            current_app.logger.info(f"Workspace {workspace_id} stopped by user {current_user.id}")
            return jsonify({'success': True, 'message': 'Workspace stopped successfully'}), 200
        else:
            return jsonify({'error': result.get('message', 'Failed to stop workspace')}), 500

    except WorkspaceProvisionerError as e:
        current_app.logger.error(f"Error stopping workspace {workspace_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:workspace_id>/restart', methods=['POST'])
@login_required
@require_workspace_ownership
def restart(workspace_id):
    """Restart workspace code-server service."""
    workspace = Workspace.query.get_or_404(workspace_id)

    provisioner = WorkspaceProvisioner()

    try:
        # Restart code-server systemd service
        result = provisioner.restart_workspace_service(workspace)

        if result['success']:
            # Update workspace status
            workspace.is_running = True
            workspace.last_started_at = db.func.now()
            workspace.status = 'running'
            db.session.commit()

            # Audit log
            AuditLogger.log_workspace_action(workspace, 'restart', current_user.id)

            current_app.logger.info(f"Workspace {workspace_id} restarted by user {current_user.id}")
            return jsonify({'success': True, 'message': 'Workspace restarted successfully'}), 200
        else:
            return jsonify({'error': result.get('message', 'Failed to restart workspace')}), 500

    except WorkspaceProvisionerError as e:
        current_app.logger.error(f"Error restarting workspace {workspace_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:workspace_id>/status', methods=['GET'])
@login_required
@require_workspace_ownership
def status(workspace_id):
    """Get workspace current status and metrics."""
    workspace = Workspace.query.get_or_404(workspace_id)

    provisioner = WorkspaceProvisioner()

    try:
        # Get real-time service status
        service_status = provisioner.get_workspace_service_status(workspace)

        return jsonify({
            'success': True,
            'workspace_id': workspace.id,
            'is_running': workspace.is_running,
            'status': workspace.status,
            'last_started_at': workspace.last_started_at.isoformat() if workspace.last_started_at else None,
            'last_stopped_at': workspace.last_stopped_at.isoformat() if workspace.last_stopped_at else None,
            'last_accessed_at': workspace.last_accessed_at.isoformat() if workspace.last_accessed_at else None,
            'service_status': service_status,
            'cpu_limit_percent': workspace.cpu_limit_percent,
            'memory_limit_mb': workspace.memory_limit_mb,
            'auto_stop_hours': workspace.auto_stop_hours
        }), 200

    except WorkspaceProvisionerError as e:
        current_app.logger.error(f"Error getting workspace {workspace_id} status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:workspace_id>/logs', methods=['GET'])
@login_required
@require_workspace_ownership
def logs(workspace_id):
    """Get workspace code-server logs."""
    workspace = Workspace.query.get_or_404(workspace_id)

    # Get optional query parameters
    lines = request.args.get('lines', 100, type=int)
    since = request.args.get('since', None)  # e.g., "1 hour ago", "2024-01-01"

    provisioner = WorkspaceProvisioner()

    try:
        # Fetch logs from systemd journal
        logs_data = provisioner.get_workspace_logs(workspace, lines=lines, since=since)

        return jsonify({
            'success': True,
            'workspace_id': workspace.id,
            'logs': logs_data['logs'],
            'lines_returned': len(logs_data['logs']),
            'truncated': logs_data.get('truncated', False)
        }), 200

    except WorkspaceProvisionerError as e:
        current_app.logger.error(f"Error getting workspace {workspace_id} logs: {str(e)}")
        return jsonify({'error': str(e)}), 500
