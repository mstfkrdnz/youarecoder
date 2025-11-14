"""
Flask configuration module with environment-based settings.
"""
import os
from datetime import timedelta
from urllib.parse import quote_plus

class Config:
    """Base configuration class with default settings."""

    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # Database settings
    DB_USER = os.environ.get('DB_USER', 'youarecoder_user')
    DB_PASS = os.environ.get('DB_PASS', 'YouAreCoderDB2025')
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '5432')
    DB_NAME = os.environ.get('DB_NAME', 'youarecoder')

    # Build connection URI - handle Unix socket paths
    if DB_HOST.startswith('/'):
        # Unix socket connection (peer authentication)
        SQLALCHEMY_DATABASE_URI = f'postgresql://{DB_USER}@/{DB_NAME}?host={quote_plus(DB_HOST)}'
    else:
        # TCP connection
        SQLALCHEMY_DATABASE_URI = f'postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False  # Set to True for SQL query logging

    # Session settings
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = True  # HTTPS connections (via Traefik)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_DOMAIN = None  # Use current domain (youarecoder.com)

    # Security
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    WTF_CSRF_SSL_STRICT = False  # Required: Flask app is behind Traefik (SSL terminating proxy)

    # Rate limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URL = 'memory://'

    # Workspace settings
    WORKSPACE_PORT_RANGE_START = 8001
    WORKSPACE_PORT_RANGE_END = 8100
    CODE_SERVER_BASE_PORT = 8001

    # File paths
    WORKSPACE_BASE_DIR = '/home'

    # Email configuration (Mailjet SMTP)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'in-v3.mailjet.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')  # Mailjet API Key
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')  # Mailjet Secret Key
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@youarecoder.com')
    MAIL_MAX_EMAILS = None
    MAIL_ASCII_ATTACHMENTS = False

    # PayTR Payment Gateway Configuration
    PAYTR_MERCHANT_ID = os.environ.get('PAYTR_MERCHANT_ID', '')
    PAYTR_MERCHANT_KEY = os.environ.get('PAYTR_MERCHANT_KEY', '')
    PAYTR_MERCHANT_SALT = os.environ.get('PAYTR_MERCHANT_SALT', '')
    PAYTR_TEST_MODE = os.environ.get('PAYTR_TEST_MODE', '1')  # '1' for test, '0' for production
    PAYTR_TIMEOUT_LIMIT = os.environ.get('PAYTR_TIMEOUT_LIMIT', '30')  # minutes

    # Base URL for payment callbacks
    BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5000')

    # Trial Configuration
    TRIAL_DAYS = 14

    # Multi-Currency Support (PayTR USD/EUR Approved)
    SUPPORTED_CURRENCIES = ['TRY', 'USD', 'EUR']
    DEFAULT_CURRENCY = 'USD'  # USD as default (changed from TRY for billing page)

    # Currency symbols for display
    CURRENCY_SYMBOLS = {
        'TRY': '₺',
        'USD': '$',
        'EUR': '€'
    }

    # Base USD Prices (Single Source of Truth)
    BASE_PRICES_USD = {
        'starter': 29,
        'team': 99,
        'enterprise': 299
    }

    @staticmethod
    def get_plan_prices(plan_key):
        """
        Get plan prices with dynamic currency conversion.

        Converts USD base prices to TRY and EUR using latest TCMB exchange rates.
        Falls back to static prices if exchange rates are unavailable.

        Args:
            plan_key: Plan identifier ('starter', 'team', 'enterprise')

        Returns:
            dict: {'TRY': int, 'USD': int, 'EUR': int, 'rate_date': 'YYYY-MM-DD' or None}
        """
        from app.models import ExchangeRate

        usd_price = Config.BASE_PRICES_USD.get(plan_key)
        if not usd_price:
            raise ValueError(f"Invalid plan key: {plan_key}")

        # Try dynamic conversion with TCMB rates
        try:
            try_price = ExchangeRate.calculate_try_price(usd_price)
            eur_price = ExchangeRate.calculate_eur_price(usd_price)

            # Get rate date for display
            usd_rate = ExchangeRate.get_latest_rate('USD', 'TRY')
            rate_date = usd_rate.effective_date.isoformat() if usd_rate else None

            return {
                'TRY': try_price,
                'USD': usd_price,
                'EUR': eur_price,
                'rate_date': rate_date
            }
        except Exception:
            # Fallback to static prices if exchange rate unavailable
            static_plan = Config.PLANS.get(plan_key, {})
            static_prices = static_plan.get('prices', {})

            return {
                'TRY': static_prices.get('TRY', usd_price * 30),  # Fallback: 30 TRY/USD
                'USD': usd_price,
                'EUR': static_prices.get('EUR', int(usd_price * 0.92)),  # Fallback: 0.92 EUR/USD
                'rate_date': None
            }

    # Subscription Plans with Multi-Currency Pricing (DEPRECATED: Use get_plan_prices())
    # Kept for backward compatibility during migration
    PLANS = {
        'starter': {
            'name': 'Starter',
            'prices': {
                'TRY': 870,      # ₺870/month
                'USD': 29,       # $29/month
                'EUR': 27        # €27/month
            },
            'max_workspaces': 5,
            'storage_per_workspace_gb': 10,
            'features': [
                '5 Development Workspaces',
                '10GB Storage per Workspace',
                'Code-Server IDE',
                'SSL Certificates',
                'Email Support'
            ],
            'popular': False
        },
        'team': {
            'name': 'Team',
            'prices': {
                'TRY': 2970,     # ₺2,970/month
                'USD': 99,       # $99/month
                'EUR': 92        # €92/month
            },
            'max_workspaces': 20,
            'storage_per_workspace_gb': 50,
            'features': [
                '20 Development Workspaces',
                '50GB Storage per Workspace',
                'Code-Server IDE',
                'SSL Certificates',
                'Priority Support',
                'Team Collaboration Tools'
            ],
            'popular': True
        },
        'enterprise': {
            'name': 'Enterprise',
            'prices': {
                'TRY': 8970,     # ₺8,970/month
                'USD': 299,      # $299/month
                'EUR': 279       # €279/month
            },
            'max_workspaces': 150,     # Enterprise limit
            'storage_per_workspace_gb': 250,
            'features': [
                'Up to 150 Development Workspaces',
                '250GB Storage per Workspace',
                'Code-Server IDE',
                'SSL Certificates',
                'Dedicated Support',
                'Custom Integrations',
                'SLA Guarantee'
            ],
            'popular': False
        }
    }


class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True
    TESTING = False
    SQLALCHEMY_ECHO = True
    SESSION_COOKIE_SECURE = False  # Allow HTTP in development
    RATELIMIT_ENABLED = False  # Disable rate limiting in development

    # Mock provisioning for development (no root privileges needed)
    MOCK_PROVISIONING = os.environ.get('MOCK_PROVISIONING', 'True') == 'True'

    # Email settings for development
    MAIL_SUPPRESS_SEND = True  # Don't send real emails, print to console
    MAIL_DEBUG = True


class ProductionConfig(Config):
    """Production environment configuration."""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True

    # Email settings for production
    MAIL_SUPPRESS_SEND = False  # Send real emails via Mailjet
    MAIL_DEBUG = False

    # Production secrets - use environment variable or inherit from Config
    # Note: SECRET_KEY should be set via environment variable in production


class TestConfig(Config):
    """Test environment configuration."""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'  # Use SQLite in-memory database for tests
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
    SESSION_COOKIE_SECURE = False

    # Email settings for testing
    MAIL_SUPPRESS_SEND = True  # Don't send emails during tests
    MAIL_DEBUG = False


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'test': TestConfig,
    'default': DevelopmentConfig
}


def get_config():
    """Get configuration based on environment variable."""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])
