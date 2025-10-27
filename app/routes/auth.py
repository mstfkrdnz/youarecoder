"""
Authentication routes (login, logout, register).
"""
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db, limiter
from app.models import User, Company, LoginAttempt
from app.forms import LoginForm, RegistrationForm

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")  # Stricter limit for login attempts
def login():
    """User login route with failed attempt tracking."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')

        # Check if account is locked
        if user and user.is_account_locked():
            # Log failed attempt
            attempt = LoginAttempt(
                email=form.email.data,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                failure_reason='account_locked'
            )
            db.session.add(attempt)
            db.session.commit()

            minutes_remaining = int((user.account_locked_until - datetime.utcnow()).total_seconds() / 60)
            flash(f'Account locked due to multiple failed login attempts. Try again in {minutes_remaining} minutes.', 'error')
            return render_template('auth/login.html', form=form)

        # Check credentials
        if user and user.check_password(form.password.data) and user.is_active:
            # Successful login
            login_user(user, remember=form.remember_me.data)
            user.last_login = datetime.utcnow()
            user.reset_failed_logins()

            # Log successful attempt
            attempt = LoginAttempt(
                email=form.email.data,
                ip_address=ip_address,
                user_agent=user_agent,
                success=True
            )
            db.session.add(attempt)
            db.session.commit()

            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.dashboard'))
        else:
            # Failed login
            if user:
                user.record_failed_login()

                # Determine failure reason
                if not user.is_active:
                    failure_reason = 'inactive_account'
                else:
                    failure_reason = 'invalid_password'
            else:
                failure_reason = 'invalid_email'

            # Log failed attempt
            attempt = LoginAttempt(
                email=form.email.data,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                failure_reason=failure_reason
            )
            db.session.add(attempt)
            db.session.commit()

            flash('Invalid email or password', 'error')

    return render_template('auth/login.html', form=form)


@bp.route('/logout')
@login_required
def logout():
    """User logout route."""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('main.index'))


@bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per hour")  # Strict limit for registrations
def register():
    """Company and user registration route."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = RegistrationForm()
    if form.validate_on_submit():
        # Validation
        if Company.query.filter_by(subdomain=form.subdomain.data).first():
            flash('Subdomain already taken', 'error')
            return render_template('auth/register.html', form=form)

        if User.query.filter_by(email=form.email.data).first():
            flash('Email already registered', 'error')
            return render_template('auth/register.html', form=form)

        # Create company
        company = Company(
            name=form.company_name.data,
            subdomain=form.subdomain.data,
            plan='starter',
            max_workspaces=1
        )
        db.session.add(company)
        db.session.flush()

        # Create admin user
        user = User(
            email=form.email.data,
            username=form.username.data,
            full_name=form.full_name.data,
            role='admin',
            company_id=company.id
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)
