"""
Workspace routes (create, delete, manage).
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, make_response
from flask_login import login_required, current_user
from app import db
from app.models import Workspace
from app.forms import WorkspaceForm
from app.services.workspace_provisioner import WorkspaceProvisioner, WorkspaceProvisionerError
from app.services.email_service import send_workspace_ready_email
from app.services.audit_logger import AuditLogger, WorkspaceSessionTracker
from app.utils.decorators import require_workspace_ownership

bp = Blueprint('workspace', __name__, url_prefix='/workspace')

@bp.route('/')
@login_required
def list():
    """List all workspaces for current company."""
    workspaces = Workspace.query.filter_by(company_id=current_user.company_id).all()
    return render_template('workspace/list.html', workspaces=workspaces)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create new workspace route with full provisioning."""
    form = WorkspaceForm()

    if form.validate_on_submit():
        # Check if company can create more workspaces
        if not current_user.company.can_create_workspace():
            flash('Workspace limit reached for your plan', 'error')
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
            workspace = Workspace(
                name=form.name.data,
                subdomain=f"{current_user.company.subdomain}-{form.name.data}",
                linux_username=f"{current_user.company.subdomain}_{sanitized_name}",
                port=port,
                code_server_password=code_server_password,
                company_id=current_user.company.id,
                owner_id=current_user.id,
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
