"""
Billing Routes for PayTR Payment Integration

Endpoints:
- POST /billing/subscribe/<plan> - Initiate payment for subscription plan
- POST /billing/callback - PayTR payment callback webhook
- GET /billing/payment/success - Success redirect after payment
- GET /billing/payment/fail - Failure redirect after payment
- GET /billing - Billing dashboard and subscription management
"""
import logging
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user

from app.services.paytr_service import PayTRService
from app.models import Payment, Invoice
from app.services.audit_logger import AuditLogger

logger = logging.getLogger(__name__)

# Create billing blueprint
bp = Blueprint('billing', __name__, url_prefix='/billing')


@bp.route('/debug-config', methods=['GET'])
@login_required
def debug_config():
    """Debug endpoint to check PayTR configuration (development only)."""
    from flask import current_app

    config_info = {
        'merchant_id': current_app.config.get('PAYTR_MERCHANT_ID', 'NOT SET'),
        'merchant_key_length': len(current_app.config.get('PAYTR_MERCHANT_KEY', '')),
        'merchant_salt_length': len(current_app.config.get('PAYTR_MERCHANT_SALT', '')),
        'test_mode': current_app.config.get('PAYTR_TEST_MODE', 'NOT SET'),
        'base_url': current_app.config.get('BASE_URL', 'NOT SET')
    }

    return jsonify(config_info)


@bp.route('/subscribe/<plan>', methods=['POST'])
@login_required
def subscribe(plan):
    """
    Initiate payment for a subscription plan.

    This endpoint generates a PayTR iframe token for the selected plan
    and returns the iframe URL for embedding in the frontend.

    Args:
        plan: Plan tier (starter, team, enterprise)

    Returns:
        JSON response:
            Success: {success: true, iframe_url: str, payment_id: int, merchant_oid: str}
            Failure: {error: str}, HTTP 400/500

    Authentication:
        Requires authenticated user session
    """
    try:
        # Validate plan exists in config
        from flask import current_app
        plans = current_app.config.get('PLANS', {})

        if plan not in plans:
            logger.warning(f"Invalid plan requested: {plan} by user {current_user.id}")
            return jsonify({'error': f'Invalid plan: {plan}'}), 400

        # Get user's IP address
        user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ',' in user_ip:
            user_ip = user_ip.split(',')[0].strip()

        # Get user's company
        company = current_user.company

        # Get currency from request (default to company preference or TRY)
        currency = request.form.get('currency') or request.json.get('currency') if request.is_json else None
        if not currency:
            currency = company.preferred_currency or current_app.config.get('DEFAULT_CURRENCY', 'TRY')

        # Validate currency
        supported_currencies = current_app.config.get('SUPPORTED_CURRENCIES', ['TRY'])
        if currency not in supported_currencies:
            logger.warning(f"Invalid currency {currency} requested by user {current_user.id}")
            return jsonify({'error': f'Invalid currency. Supported: {", ".join(supported_currencies)}'}), 400

        # Generate PayTR iframe token with selected currency
        paytr_service = PayTRService()
        result = paytr_service.generate_iframe_token(
            company=company,
            plan=plan,
            user_ip=user_ip,
            user_email=current_user.email,
            currency=currency  # Multi-currency support (TRY, USD, EUR)
        )

        if result['success']:
            logger.info(f"Payment initiated for company {company.id}, "
                       f"plan {plan}, payment_id {result['payment_id']}")

            # Audit log: payment initiated
            AuditLogger.log(
                action_type='payment_initiated',
                resource_type='payment',
                resource_id=result.get('payment_id'),
                details={
                    'plan': plan,
                    'merchant_oid': result.get('merchant_oid'),
                    'currency': 'TRY'
                },
                success=True
            )

            return jsonify(result), 200
        else:
            logger.error(f"Payment initiation failed for company {company.id}: {result['reason']}")

            # Audit log: payment initiation failed
            AuditLogger.log(
                action_type='payment_initiation_failed',
                resource_type='payment',
                resource_id=None,
                details={
                    'plan': plan,
                    'reason': result['reason']
                },
                success=False,
                error_message=result['reason']
            )

            return jsonify({'error': result['reason']}), 500

    except ValueError as e:
        logger.error(f"Validation error in subscribe: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error in subscribe: {str(e)}", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred'}), 500


@bp.route('/callback', methods=['POST'])
def payment_callback():
    """
    PayTR payment callback webhook.

    This endpoint receives payment notifications from PayTR after
    a payment is processed. It verifies the hash and updates the
    payment status, subscription, and generates invoices.

    Request Body (POST form data from PayTR):
        - merchant_oid: Unique order identifier
        - status: Payment status ('success' or 'failed')
        - total_amount: Payment amount in cents
        - hash: HMAC-SHA256 security hash
        - test_mode: '1' if test transaction
        - payment_type: Payment method used
        - failed_reason_code: Error code if failed
        - failed_reason_msg: Error message if failed

    Returns:
        "OK" (200) if processed successfully
        Error message (400/404/500) if processing failed

    Security:
        - CSRF exempt (external webhook)
        - Hash verification prevents fraud
        - Only processes verified PayTR notifications
    """
    try:
        # Get POST data from PayTR
        post_data = request.form.to_dict()

        logger.info(f"Received payment callback for merchant_oid: {post_data.get('merchant_oid')}")

        # Process callback through service
        paytr_service = PayTRService()
        success, message = paytr_service.process_payment_callback(post_data)

        if success:
            logger.info(f"Payment callback processed successfully: {message}")

            # Audit log: successful payment callback
            AuditLogger.log(
                action_type='payment_callback_success',
                resource_type='payment',
                resource_id=None,  # merchant_oid in details
                details={
                    'merchant_oid': post_data.get('merchant_oid'),
                    'status': post_data.get('status'),
                    'amount': post_data.get('total_amount'),
                    'payment_type': post_data.get('payment_type'),
                    'test_mode': post_data.get('test_mode')
                },
                success=True
            )

            return message, 200
        else:
            logger.error(f"Payment callback processing failed: {message}")

            # Audit log: failed payment callback
            AuditLogger.log(
                action_type='payment_callback_failure',
                resource_type='payment',
                resource_id=None,
                details={
                    'merchant_oid': post_data.get('merchant_oid'),
                    'status': post_data.get('status'),
                    'failed_reason_code': post_data.get('failed_reason_code'),
                    'failed_reason_msg': post_data.get('failed_reason_msg'),
                    'error_message': message
                },
                success=False,
                error_message=message
            )

            # Return appropriate HTTP status
            if 'Invalid hash' in message:
                return message, 400
            elif 'not found' in message.lower():
                return message, 404
            else:
                return message, 500

    except Exception as e:
        logger.error(f"Unexpected error in payment_callback: {str(e)}", exc_info=True)
        return 'Processing error', 500


@bp.route('/payment/success')
def payment_success():
    """
    Payment success redirect page.

    Users are redirected here by PayTR after successful payment.
    Displays success message and next steps.

    Query Parameters:
        - merchant_oid (optional): Payment order ID
        - token (optional): PayTR token

    Returns:
        HTML page with success message
    """
    merchant_oid = request.args.get('merchant_oid')

    logger.info(f"User redirected to success page, merchant_oid: {merchant_oid}")

    return render_template('billing/success.html',
                         merchant_oid=merchant_oid,
                         title='Payment Successful')


@bp.route('/payment/fail')
def payment_fail():
    """
    Payment failure redirect page.

    Users are redirected here by PayTR after failed payment.
    Displays error message and retry options.

    Query Parameters:
        - reason (optional): Failure reason
        - merchant_oid (optional): Payment order ID

    Returns:
        HTML page with failure message
    """
    reason = request.args.get('reason', 'Payment processing failed')
    merchant_oid = request.args.get('merchant_oid')

    logger.warning(f"User redirected to fail page, merchant_oid: {merchant_oid}, reason: {reason}")

    return render_template('billing/fail.html',
                         reason=reason,
                         merchant_oid=merchant_oid,
                         title='Payment Failed')


@bp.route('/')
@login_required
def billing_dashboard():
    """
    Billing and subscription management dashboard.

    Displays current subscription status, payment history,
    invoices, and subscription management options.

    Authentication:
        Requires authenticated user session

    Returns:
        HTML billing dashboard page
    """
    try:
        company = current_user.company
        subscription = company.subscription
        # Only show completed payments (success or failed), hide pending payments
        payments = company.payments.filter(
            Payment.status.in_(['success', 'failed'])
        ).order_by(Payment.created_at.desc()).limit(10).all()
        invoices = company.invoices.order_by(Invoice.created_at.desc()).limit(10).all()

        # Get plan details from config with dynamic pricing
        from flask import current_app
        from config import Config

        plans = current_app.config.get('PLANS', {})

        # Get dynamic prices for all plans
        dynamic_prices = {}
        for plan_key in ['starter', 'team', 'enterprise']:
            try:
                dynamic_prices[plan_key] = Config.get_plan_prices(plan_key)
            except Exception as e:
                logger.warning(f"Failed to get dynamic prices for {plan_key}: {str(e)}")
                # Fallback to static prices from PLANS
                dynamic_prices[plan_key] = {
                    'TRY': plans.get(plan_key, {}).get('prices', {}).get('TRY', 0),
                    'USD': plans.get(plan_key, {}).get('prices', {}).get('USD', 0),
                    'EUR': plans.get(plan_key, {}).get('prices', {}).get('EUR', 0),
                    'rate_date': None
                }

        logger.info(f"Billing dashboard accessed by user {current_user.id}")

        return render_template('billing/dashboard.html',
                             company=company,
                             subscription=subscription,
                             payments=payments,
                             invoices=invoices,
                             plans=plans,
                             dynamic_prices=dynamic_prices,
                             title='Billing & Subscription')

    except Exception as e:
        logger.error(f"Error loading billing dashboard: {str(e)}", exc_info=True)
        flash('Error loading billing information', 'error')
        return redirect(url_for('main.index'))


# CSRF exemption for PayTR callback
# This must be done in app initialization after CSRF is initialized
def init_billing_csrf_exempt(csrf):
    """
    Exempt payment callback from CSRF protection.

    This function should be called during app initialization
    after CSRF protection is set up.

    Args:
        csrf: Flask-WTF CSRFProtect instance
    """
    csrf.exempt(payment_callback)
