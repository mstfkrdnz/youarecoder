"""
Authentication routes (login, logout, register).
"""
from datetime import datetime, timedelta
from urllib.parse import urlparse, urljoin
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app import db, limiter
from app.models import User, Company, LoginAttempt
from app.forms import LoginForm, RegistrationForm
from app.services.email_service import send_registration_email
from app.services.audit_logger import AuditLogger

bp = Blueprint('auth', __name__, url_prefix='/auth')


def is_safe_url(target):
    """
    Check if redirect URL is safe (prevent open redirect vulnerability).

    Args:
        target: The URL to validate

    Returns:
        bool: True if URL is safe to redirect to
    """
    if not target:
        return False

    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))

    # Allow redirects to same host or any *.youarecoder.com subdomain
    return (test_url.scheme in ('http', 'https') and
            (test_url.netloc == ref_url.netloc or
             test_url.netloc.endswith('.youarecoder.com')))


def get_real_ip():
    """
    Get real client IP address, handling reverse proxy (Traefik).

    Checks X-Forwarded-For header first (set by Traefik), then falls back to
    X-Real-IP, and finally request.remote_addr.

    Returns:
        str: Client IP address
    """
    # X-Forwarded-For can contain multiple IPs: "client, proxy1, proxy2"
    # We want the first one (original client)
    if request.headers.get('X-Forwarded-For'):
        # Get first IP in the chain (original client)
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()

    # Fallback to X-Real-IP (some reverse proxies use this)
    if request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')

    # Last resort: direct connection IP (will be 127.0.0.1 behind proxy)
    return request.remote_addr


@bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")  # Stricter limit for login attempts
def login():
    """User login route with failed attempt tracking."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = LoginForm()

    # Get next parameter from query string (GET) or form data (POST)
    next_page = request.args.get('next') or request.form.get('next')

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        ip_address = get_real_ip()
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

            # Audit log: successful login
            AuditLogger.log_login(user, success=True)

            # Handle redirect after login with security validation
            if next_page and is_safe_url(next_page):
                return redirect(next_page)

            return redirect(url_for('main.dashboard'))
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

            # Audit log: failed login
            AuditLogger.log_login(user, success=False, failure_reason=failure_reason)

            flash('Invalid email or password', 'error')

    return render_template('auth/login.html', form=form, next=next_page)


@bp.route('/logout')
@login_required
def logout():
    """User logout route."""
    # Audit log: logout (before logout_user() so we still have current_user)
    AuditLogger.log_logout(current_user)

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
        if Company.query.filter_by(name=form.company_name.data).first():
            flash('Company name already registered', 'error')
            return render_template('auth/register.html', form=form)

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

        # Create admin user with initial quota of 1
        user = User(
            email=form.email.data,
            full_name=form.full_name.data,
            role='admin',
            company_id=company.id,
            workspace_quota=1,
            quota_assigned_at=datetime.utcnow()
        )
        user.set_password(form.password.data)

        # Save legal acceptance with real client IP
        client_ip = get_real_ip()
        user.terms_accepted = True
        user.terms_accepted_at = datetime.utcnow()
        user.terms_accepted_ip = client_ip
        user.terms_version = "1.0"

        user.privacy_accepted = True
        user.privacy_accepted_at = datetime.utcnow()
        user.privacy_accepted_ip = client_ip
        user.privacy_version = "1.0"

        db.session.add(user)
        db.session.commit()

        # Send welcome email
        try:
            send_registration_email(user)
            current_app.logger.info(f"Welcome email sent to {user.email}")
        except Exception as e:
            current_app.logger.error(f"Failed to send welcome email to {user.email}: {str(e)}")

        flash('Registration successful! Check your email and then log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)
