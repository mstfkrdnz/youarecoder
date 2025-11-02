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
        200: User is authenticated
        302: User not authenticated - redirect to login
    """
    # Check if user is authenticated via Flask-Login
    if current_user.is_authenticated:
        # Return 200 with user info in headers
        response = jsonify({'authenticated': True})
        response.headers['X-Auth-User'] = current_user.email
        response.headers['X-Auth-User-ID'] = str(current_user.id)
        response.headers['X-Auth-Company'] = current_user.company.subdomain if current_user.company else ''
        return response, 200

    # User not authenticated - redirect to login page with return URL
    # Get the original workspace URL from custom X-Workspace-Host header
    # (set by workspace-specific headers middleware in Traefik)
    workspace_host = request.headers.get('X-Workspace-Host')

    if workspace_host:
        # We have the actual workspace hostname
        original_uri = request.headers.get('X-Forwarded-Uri', '/')
        original_proto = request.headers.get('X-Forwarded-Proto', 'https')
        return_url = f"{original_proto}://{workspace_host}{original_uri}"
    else:
        # Fallback: redirect to main site (shouldn't happen with proper middleware)
        return_url = "https://youarecoder.com/"

    # Redirect to login page with next parameter
    login_url = f"https://youarecoder.com/auth/login?next={quote(return_url)}"

    response = redirect(login_url, code=302)
    return response
