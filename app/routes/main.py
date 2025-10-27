"""
Main routes (index, dashboard).
"""
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    """Landing page route."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('landing.html')


@bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard route."""
    workspaces = current_user.workspaces.order_by('created_at desc').limit(6).all()
    company = current_user.company

    return render_template('dashboard.html',
                          workspaces=workspaces,
                          company=company)
