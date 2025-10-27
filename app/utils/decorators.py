"""
Custom decorators for authorization and access control.
"""
from functools import wraps
from flask import abort
from flask_login import current_user
from app.models import Workspace


def require_workspace_ownership(f):
    """
    Decorator to ensure the current user's company owns the workspace.

    Usage:
        @bp.route('/workspaces/<int:workspace_id>/delete')
        @login_required
        @require_workspace_ownership
        def delete_workspace(workspace_id):
            ...

    Raises:
        403 Forbidden if workspace doesn't belong to user's company
        404 Not Found if workspace doesn't exist
    """
    @wraps(f)
    def decorated_function(workspace_id, *args, **kwargs):
        workspace = Workspace.query.get_or_404(workspace_id)

        if workspace.company_id != current_user.company_id:
            abort(403)  # Forbidden - not your workspace

        return f(workspace_id, *args, **kwargs)

    return decorated_function


def require_role(*roles):
    """
    Decorator to require specific user role(s).

    Args:
        *roles: Variable number of role names ('admin', 'user')

    Usage:
        @bp.route('/admin/users')
        @login_required
        @require_role('admin')
        def list_users():
            ...

    Raises:
        403 Forbidden if user doesn't have required role
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)  # Forbidden - insufficient permissions

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def require_company_admin(f):
    """
    Decorator to require admin role within company.

    Shorthand for @require_role('admin')

    Usage:
        @bp.route('/company/settings')
        @login_required
        @require_company_admin
        def company_settings():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.role != 'admin':
            abort(403)  # Forbidden - admin only

        return f(*args, **kwargs)

    return decorated_function
