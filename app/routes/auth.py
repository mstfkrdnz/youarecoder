"""
Authentication routes (login, logout, register).
"""
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User, Company

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login route."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember', False)

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password) and user.is_active:
            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            db.session.commit()

            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.dashboard'))
        else:
            flash('Invalid email or password', 'error')

    return render_template('auth/login.html')


@bp.route('/logout')
@login_required
def logout():
    """User logout route."""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('main.index'))


@bp.route('/register', methods=['GET', 'POST'])
def register():
    """Company and user registration route."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        # Company details
        company_name = request.form.get('company_name')
        subdomain = request.form.get('subdomain')

        # User details
        email = request.form.get('email')
        username = request.form.get('username')
        full_name = request.form.get('full_name')
        password = request.form.get('password')

        # Validation
        if Company.query.filter_by(subdomain=subdomain).first():
            flash('Subdomain already taken', 'error')
            return render_template('auth/register.html')

        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('auth/register.html')

        # Create company
        company = Company(
            name=company_name,
            subdomain=subdomain,
            plan='starter',
            max_workspaces=1
        )
        db.session.add(company)
        db.session.flush()

        # Create admin user
        user = User(
            email=email,
            username=username,
            full_name=full_name,
            role='admin',
            company_id=company.id
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')
