"""
Workspace routes (create, delete, manage).
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Workspace

bp = Blueprint('workspace', __name__, url_prefix='/workspace')


@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create new workspace route."""
    if request.method == 'POST':
        name = request.form.get('name')

        # Check if company can create more workspaces
        if not current_user.company.can_create_workspace():
            flash('Workspace limit reached for your plan', 'error')
            return redirect(url_for('main.dashboard'))

        # Create workspace (provisioning will be implemented later)
        workspace = Workspace(
            name=name,
            subdomain=f"{name}.{current_user.company.subdomain}",
            linux_username=f"{current_user.company.subdomain}_{name}",
            port=8001,  # Will be assigned dynamically later
            code_server_password='temp_password',  # Will be generated later
            company_id=current_user.company.id,
            owner_id=current_user.id,
            status='pending'
        )
        db.session.add(workspace)
        db.session.commit()

        flash(f'Workspace "{name}" created successfully!', 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('workspace/create.html')


@bp.route('/<int:workspace_id>/delete', methods=['POST'])
@login_required
def delete(workspace_id):
    """Delete workspace route."""
    workspace = Workspace.query.get_or_404(workspace_id)

    # Check ownership
    if workspace.owner_id != current_user.id and not current_user.is_admin():
        flash('Permission denied', 'error')
        return redirect(url_for('main.dashboard'))

    db.session.delete(workspace)
    db.session.commit()

    flash(f'Workspace "{workspace.name}" deleted', 'info')
    return redirect(url_for('main.dashboard'))


@bp.route('/<int:workspace_id>')
@login_required
def view(workspace_id):
    """View workspace details route."""
    workspace = Workspace.query.get_or_404(workspace_id)

    # Check access
    if workspace.company_id != current_user.company_id:
        flash('Permission denied', 'error')
        return redirect(url_for('main.dashboard'))

    return render_template('workspace/view.html', workspace=workspace)
