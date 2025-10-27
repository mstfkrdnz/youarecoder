"""
Main routes (index, dashboard).
"""
from flask import Blueprint, render_template
from flask_login import login_required, current_user

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    """Landing page route."""
    return render_template('index.html')


@bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard route."""
    workspaces = current_user.workspaces.all()
    company = current_user.company

    return render_template('dashboard.html',
                          workspaces=workspaces,
                          company=company)
