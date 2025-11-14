"""
ForwardAuth endpoint for Traefik authentication.
"""
from flask import Blueprint, request, jsonify, session, redirect, url_for, current_app
from flask_login import current_user
from functools import wraps
from urllib.parse import quote

bp = Blueprint('auth_verify', __name__)

@bp.route('/api/auth/verify', methods=['GET', 'HEAD'])
def verify_auth():
    """
    Traefik ForwardAuth endpoint.

    Returns:
        200: User is authenticated and owns the workspace
        302: User not authenticated - redirect to login
        403: User authenticated but does not own workspace
    """
    # Check if user is authenticated via Flask-Login
    if current_user.is_authenticated:
        # Get workspace subdomain from X-Workspace-Host header
        workspace_host = request.headers.get('X-Workspace-Host')

        if workspace_host:
            # Extract subdomain from workspace_host (e.g., "alkedos-w311" from "alkedos-w311.youarecoder.com")
            workspace_subdomain = workspace_host.split('.')[0]

            # Check if user owns this workspace
            from app.models import Workspace
            workspace = Workspace.query.filter_by(subdomain=workspace_subdomain).first()

            if workspace:
                # Verify user owns the workspace (through company ownership)
                if workspace.company_id == current_user.company_id:
                    # User owns the workspace - allow access
                    response = jsonify({'authenticated': True})
                    response.headers['X-Auth-User'] = current_user.email
                    response.headers['X-Auth-User-ID'] = str(current_user.id)
                    response.headers['X-Auth-Company'] = current_user.company.subdomain if current_user.company else ''
                    return response, 200
                else:
                    # User authenticated but does not own this workspace
                    return jsonify({'error': 'Forbidden: You do not own this workspace'}), 403
            else:
                # Workspace not found
                return jsonify({'error': 'Workspace not found'}), 404

        # No workspace host header - allow access (main site)
        response = jsonify({'authenticated': True})
        response.headers['X-Auth-User'] = current_user.email
        response.headers['X-Auth-User-ID'] = str(current_user.id)
        response.headers['X-Auth-Company'] = current_user.company.subdomain if current_user.company else ''
        return response, 200

    # User not authenticated - redirect to login page with return URL
    workspace_host = request.headers.get('X-Workspace-Host')

    if workspace_host:
        # We have the actual workspace hostname
        original_uri = request.headers.get('X-Forwarded-Uri', '/')
        original_proto = request.headers.get('X-Forwarded-Proto', 'https')
        return_url = f"{original_proto}://{workspace_host}{original_uri}"
    else:
        # Fallback: redirect to main site
        return_url = "https://youarecoder.com/"

    # Redirect to login page with next parameter
    login_url = f"https://youarecoder.com/auth/login?next={quote(return_url)}"

    response = redirect(login_url, code=302)
    return response
