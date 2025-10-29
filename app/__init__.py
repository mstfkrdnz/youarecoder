"""
Flask application factory module.
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()
csrf = CSRFProtect()
mail = Mail()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)
talisman = Talisman()


def create_app(config_name=None):
    """
    Flask application factory.

    Args:
        config_name: Configuration name ('development', 'production', 'test')
                    If None, uses FLASK_ENV environment variable

    Returns:
        Flask application instance
    """
    app = Flask(__name__)

    # Load configuration
    from config import config
    import os

    # Use FLASK_ENV if config_name not specified
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app.config.from_object(config[config_name])

    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    limiter.init_app(app)

    # Configure security headers (production only)
    if config_name == 'production':
        talisman.init_app(app,
            force_https=True,
            strict_transport_security=True,
            strict_transport_security_max_age=31536000,  # 1 year
            strict_transport_security_include_subdomains=True,
            content_security_policy={
                'default-src': ["'self'"],
                'script-src': [
                    "'self'",
                    'https://cdn.tailwindcss.com',
                    'https://unpkg.com',
                    'https://www.paytr.com',  # PayTR payment scripts
                    "'unsafe-inline'",  # Required for inline scripts
                    "'unsafe-eval'"  # Required for Alpine.js
                ],
                'style-src': [
                    "'self'",
                    'https://cdn.tailwindcss.com',
                    "'unsafe-inline'"  # Required for Tailwind
                ],
                'img-src': ["'self'", 'data:', 'https:'],
                'font-src': ["'self'", 'https:', 'data:'],
                'connect-src': ["'self'", 'https://www.paytr.com'],  # PayTR API
                'frame-src': ["'self'", 'https://www.paytr.com'],  # PayTR iframe
                'frame-ancestors': ["'none'"],  # Prevent clickjacking
            },
            # Disable CSP nonce for Tailwind CDN compatibility
            content_security_policy_nonce_in=[],
            feature_policy={
                'geolocation': "'none'",
                'microphone': "'none'",
                'camera': "'none'",
            },
            referrer_policy='strict-origin-when-cross-origin',
            force_file_save=False
        )

    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.session_protection = 'strong'

    # Register blueprints
    from app.routes import auth, main, workspace, api, billing, legal, admin, metrics
    app.register_blueprint(auth.bp)
    app.register_blueprint(main.bp)
    app.register_blueprint(workspace.bp)
    app.register_blueprint(api.bp)
    app.register_blueprint(billing.bp)
    app.register_blueprint(legal.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(metrics.bp)

    # Exempt billing callback from CSRF protection
    billing.init_billing_csrf_exempt(csrf)

    # User loader for Flask-Login
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register CLI commands
    from app import cli
    cli.init_app(app)

    return app
