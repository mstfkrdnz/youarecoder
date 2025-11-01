"""
PayTR Payment Gateway Service

This service handles all PayTR payment integration including:
- iFrame token generation with HMAC-SHA256 security
- Payment callback verification and processing
- Subscription lifecycle management
- Payment and invoice record creation

Security Note:
- All sensitive operations use HMAC-SHA256 hashing with merchant credentials
- Callback verification prevents fraudulent payment notifications
- Test mode support for development and staging environments
"""
import base64
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import requests

from flask import current_app
from app import db
from app.models import Company, Subscription, Payment, Invoice, Workspace
from app.services.workspace_provisioner import WorkspaceProvisioner

logger = logging.getLogger(__name__)


class PayTRService:
    """
    PayTR Payment Gateway Integration Service

    Provides secure payment processing through PayTR's iFrame API with:
    - Token generation using HMAC-SHA256 cryptographic signatures
    - Callback verification for payment notifications
    - Subscription and payment lifecycle management
    - Comprehensive error handling and logging
    """

    # PayTR API Endpoints
    TOKEN_URL = "https://www.paytr.com/odeme/api/get-token"
    IFRAME_URL = "https://www.paytr.com/odeme/guvenli/{token}"

    def __init__(self):
        """Initialize PayTR service with configuration from Flask app config."""
        self.merchant_id = current_app.config.get('PAYTR_MERCHANT_ID', '')
        self.merchant_key = current_app.config.get('PAYTR_MERCHANT_KEY', '').encode('utf-8')
        self.merchant_salt = current_app.config.get('PAYTR_MERCHANT_SALT', '')
        self.test_mode = current_app.config.get('PAYTR_TEST_MODE', '1')
        self.timeout_limit = current_app.config.get('PAYTR_TIMEOUT_LIMIT', '30')

        # Validate required configuration
        if not all([self.merchant_id, self.merchant_key, self.merchant_salt]):
            logger.error("PayTR configuration incomplete: missing merchant credentials")

    def generate_iframe_token(
        self,
        company: Company,
        plan: str,
        user_ip: str,
        user_email: str,
        payment_type: str = 'card',
        currency: str = 'TRY'
    ) -> Dict[str, any]:
        """
        Generate PayTR iFrame token for payment processing.

        This method creates a secure payment token using HMAC-SHA256 hashing
        and returns the iframe URL for embedding in the frontend.

        Args:
            company: Company model instance making the payment
            plan: Plan tier (starter, team, enterprise)
            user_ip: User's IP address for fraud prevention
            user_email: User's email for payment notification
            payment_type: Payment method ('card', 'eft', etc.)
            currency: Currency code (USD or TRY)

        Returns:
            Dict containing:
                - success (bool): Whether token generation succeeded
                - token (str): PayTR iframe token if successful
                - iframe_url (str): Complete iframe URL if successful
                - payment_id (int): Database payment record ID
                - merchant_oid (str): Unique order ID for tracking
                - reason (str): Error reason if failed

        Raises:
            ValueError: If plan is invalid or configuration is missing
            requests.RequestException: If PayTR API call fails

        Example:
            >>> service = PayTRService()
            >>> result = service.generate_iframe_token(
            ...     company=my_company,
            ...     plan='team',
            ...     user_ip='192.168.1.1',
            ...     user_email='user@example.com'
            ... )
            >>> if result['success']:
            ...     iframe_url = result['iframe_url']
        """
        try:
            # Validate plan exists
            plans = current_app.config.get('PLANS', {})
            if plan not in plans:
                raise ValueError(f"Invalid plan: {plan}")

            # Validate currency support
            supported_currencies = current_app.config.get('SUPPORTED_CURRENCIES', ['TRY'])
            if currency not in supported_currencies:
                raise ValueError(f"Unsupported currency: {currency}. Supported: {', '.join(supported_currencies)}")

            # Get dynamic pricing from Config.get_plan_prices()
            from config import Config
            try:
                plan_prices = Config.get_plan_prices(plan)

                # Get price for selected currency
                if currency not in plan_prices:
                    raise ValueError(f"Price not configured for currency: {currency}")

                amount_decimal = plan_prices[currency]

                logger.info(f"Using dynamic pricing for {plan}: {currency} {amount_decimal} (rate date: {plan_prices.get('rate_date')})")
            except Exception as e:
                # Fallback to static PLANS config if dynamic pricing fails
                logger.warning(f"Dynamic pricing failed for {plan}, using static config: {str(e)}")
                plan_config = plans[plan]

                if 'prices' in plan_config and currency in plan_config['prices']:
                    amount_decimal = plan_config['prices'][currency]
                else:
                    raise ValueError(f"Price not configured for currency: {currency}")

            # Convert to cents/kuruş (29 -> 2900)
            payment_amount = int(amount_decimal * 100)

            # Generate unique merchant order ID (alphanumeric only, no special chars)
            # Format: YAC + timestamp + company_id (e.g., YAC17300000001)
            merchant_oid = f"YAC{int(time.time())}{company.id}"

            # Create payment record in database
            payment = Payment(
                company_id=company.id,
                subscription_id=company.subscription.id if company.subscription else None,
                paytr_merchant_oid=merchant_oid,
                amount=payment_amount,
                currency=currency,
                plan=plan,  # Store plan info for callback processing
                status='pending',
                payment_type='initial',
                test_mode=(self.test_mode == '1'),
                user_ip=user_ip
            )
            db.session.add(payment)
            db.session.commit()

            logger.info(f"Created payment record {payment.id} for company {company.id}, "
                       f"plan {plan}, amount {payment_amount/100:.2f} {currency}")

            # Prepare user basket (itemized list for PayTR)
            user_basket_items = [
                [plan_config['name'], str(amount_decimal), 1]  # [item_name, price, quantity]
            ]
            user_basket = base64.b64encode(
                json.dumps(user_basket_items).encode('utf-8')
            ).decode('utf-8')

            # Installment settings (0 = no installment for subscriptions)
            no_installment = '0'
            max_installment = '0'

            # Success, failure, and callback URLs
            base_url = current_app.config.get('BASE_URL', 'https://youarecoder.com')
            merchant_ok_url = f"{base_url}/billing/payment/success"
            merchant_fail_url = f"{base_url}/billing/payment/fail"
            merchant_oid_url = f"{base_url}/billing/callback"  # PayTR notification callback

            # Generate PayTR token using HMAC-SHA256
            # Hash formula: merchant_id + user_ip + merchant_oid + email + payment_amount +
            #               user_basket + no_installment + max_installment + currency + test_mode
            hash_str = (
                f"{self.merchant_id}{user_ip}{merchant_oid}{user_email}"
                f"{payment_amount}{user_basket}{no_installment}{max_installment}"
                f"{currency}{self.test_mode}"
            )

            # Create HMAC-SHA256 hash with merchant credentials
            hash_data = (hash_str + self.merchant_salt).encode('utf-8')
            paytr_token = base64.b64encode(
                hmac.new(self.merchant_key, hash_data, hashlib.sha256).digest()
            ).decode('utf-8')

            logger.debug(f"Generated PayTR token for merchant_oid: {merchant_oid}")

            # Prepare API request parameters
            post_data = {
                'merchant_id': self.merchant_id,
                'user_ip': user_ip,
                'merchant_oid': merchant_oid,
                'email': user_email,
                'payment_amount': str(payment_amount),
                'paytr_token': paytr_token,
                'user_basket': user_basket,
                'debug_on': '1',
                'no_installment': no_installment,
                'max_installment': max_installment,
                'user_name': company.name,
                'user_address': 'Online Service',
                'user_phone': '0000000000',
                'merchant_ok_url': merchant_ok_url,
                'merchant_fail_url': merchant_fail_url,
                'merchant_oid_url': merchant_oid_url,  # Callback/notification URL (required)
                'timeout_limit': self.timeout_limit,
                'currency': currency,
                'test_mode': self.test_mode,
                'lang': 'en'
            }

            # Call PayTR API to get iframe token
            response = requests.post(
                self.TOKEN_URL,
                data=post_data,
                timeout=20,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            response.raise_for_status()

            result = response.json()

            if result.get('status') == 'success':
                token = result['token']
                iframe_url = self.IFRAME_URL.format(token=token)

                logger.info(f"PayTR token generated successfully for payment {payment.id}")

                return {
                    'success': True,
                    'token': token,
                    'iframe_token': token,  # Frontend expects iframe_token
                    'iframe_url': iframe_url,
                    'payment_id': payment.id,
                    'merchant_oid': merchant_oid
                }
            else:
                error_reason = result.get('reason', 'Unknown error')
                logger.error(f"PayTR token generation failed: {error_reason}")

                # Update payment status to failed
                payment.status = 'failed'
                payment.failure_reason_message = error_reason
                db.session.commit()

                return {
                    'success': False,
                    'reason': error_reason
                }

        except ValueError as e:
            logger.error(f"Validation error in generate_iframe_token: {str(e)}")
            return {
                'success': False,
                'reason': str(e)
            }
        except requests.RequestException as e:
            logger.error(f"PayTR API request failed: {str(e)}")
            return {
                'success': False,
                'reason': f"Payment gateway communication error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error in generate_iframe_token: {str(e)}", exc_info=True)
            return {
                'success': False,
                'reason': f"Internal error: {str(e)}"
            }

    def verify_callback_hash(self, post_data: Dict[str, str]) -> bool:
        """
        Verify PayTR callback hash for security validation.

        This method prevents fraudulent payment notifications by verifying
        the HMAC-SHA256 hash sent by PayTR matches our calculation.

        Args:
            post_data: Dictionary containing PayTR callback POST data
                Required fields:
                - merchant_oid: Unique order identifier
                - status: Payment status ('success' or 'failed')
                - total_amount: Payment amount in cents
                - hash: PayTR's HMAC-SHA256 signature

        Returns:
            bool: True if hash is valid, False otherwise

        Security:
            ALWAYS verify callback hash before processing payments.
            Invalid hash indicates potential fraud or man-in-the-middle attack.

        Example:
            >>> service = PayTRService()
            >>> if service.verify_callback_hash(request.form):
            ...     # Safe to process payment
            ...     service.process_payment_callback(request.form)
        """
        try:
            merchant_oid = post_data.get('merchant_oid', '')
            status = post_data.get('status', '')
            total_amount = post_data.get('total_amount', '')
            hash_received = post_data.get('hash', '')

            # Generate local hash using same formula as PayTR
            # Hash formula: merchant_oid + merchant_salt + status + total_amount
            hash_str = f"{merchant_oid}{self.merchant_salt}{status}{total_amount}"

            # Compute HMAC-SHA256 hash
            hash_calculated = base64.b64encode(
                hmac.new(
                    self.merchant_key,
                    hash_str.encode('utf-8'),
                    hashlib.sha256
                ).digest()
            ).decode('utf-8')

            # Constant-time comparison to prevent timing attacks
            is_valid = hmac.compare_digest(hash_calculated, hash_received)

            if not is_valid:
                logger.warning(
                    f"PayTR callback hash verification failed for merchant_oid: {merchant_oid}. "
                    f"Expected: {hash_calculated}, Received: {hash_received}"
                )

            return is_valid

        except Exception as e:
            logger.error(f"Error in verify_callback_hash: {str(e)}", exc_info=True)
            return False

    def process_payment_callback(self, post_data: Dict[str, str]) -> Tuple[bool, str]:
        """
        Process PayTR payment callback notification.

        This method handles the complete payment callback workflow:
        1. Verify callback hash for security
        2. Find payment record in database
        3. Update payment status
        4. Activate subscription if payment successful
        5. Generate invoice
        6. Send notification emails

        Args:
            post_data: PayTR callback POST data
                Fields:
                - merchant_oid: Order identifier
                - status: 'success' or 'failed'
                - total_amount: Amount in cents
                - hash: Security hash
                - failed_reason_code: Error code if failed
                - failed_reason_msg: Error message if failed
                - test_mode: '1' if test transaction
                - payment_type: Payment method used

        Returns:
            Tuple[bool, str]: (success_status, message)
                - (True, 'OK') if processed successfully
                - (False, error_message) if processing failed

        Side Effects:
            - Updates Payment record status
            - Activates/updates Subscription
            - Creates Invoice record
            - Triggers email notifications

        Example:
            >>> @app.route('/billing/callback', methods=['POST'])
            >>> def payment_callback():
            ...     service = PayTRService()
            ...     success, message = service.process_payment_callback(request.form)
            ...     return message, 200 if success else 400
        """
        try:
            # Step 1: Verify callback hash
            if not self.verify_callback_hash(post_data):
                logger.error("Callback hash verification failed - possible fraud attempt")
                return False, "Invalid hash"

            # Step 2: Extract callback data
            merchant_oid = post_data.get('merchant_oid')
            status = post_data.get('status')
            total_amount = int(post_data.get('total_amount', 0))
            test_mode = post_data.get('test_mode', '0') == '1'
            payment_type = post_data.get('payment_type', 'unknown')
            failed_reason_code = post_data.get('failed_reason_code')
            failed_reason_msg = post_data.get('failed_reason_msg')

            logger.info(f"Processing PayTR callback for merchant_oid: {merchant_oid}, "
                       f"status: {status}, amount: {total_amount/100:.2f}")

            # Step 3: Find payment record
            payment = Payment.query.filter_by(paytr_merchant_oid=merchant_oid).first()
            if not payment:
                logger.error(f"Payment not found for merchant_oid: {merchant_oid}")
                return False, "Payment not found"

            # Step 4: Update payment record
            if status == 'success':
                payment.status = 'success'
                payment.completed_at = datetime.utcnow()
                logger.info(f"Payment {payment.id} successful")

                # Step 5: Activate subscription
                company = payment.company
                subscription = company.subscription

                if not subscription:
                    # Create new subscription with plan from payment record
                    subscription = Subscription(
                        company_id=company.id,
                        plan=payment.plan,  # Use plan from payment record
                        status='active',
                        current_period_start=datetime.utcnow(),
                        current_period_end=datetime.utcnow() + timedelta(days=30)
                    )
                    db.session.add(subscription)

                    # Update company plan and workspace limits
                    company.plan = payment.plan  # Update company plan
                    plan_config = current_app.config.get('PLANS', {}).get(payment.plan, {})
                    if plan_config:
                        company.max_workspaces = plan_config.get('max_workspaces', 1)
                        logger.info(f"Updated company {company.id} to {payment.plan} plan with max_workspaces={company.max_workspaces}")

                        # Upgrade existing workspace storage to new plan limits
                        self._upgrade_workspace_storage(company, payment.plan)
                else:
                    # Update existing subscription
                    if subscription.status == 'trial':
                        # First payment after trial
                        subscription.status = 'active'
                        subscription.plan = payment.plan  # Update to paid plan
                        subscription.current_period_start = datetime.utcnow()
                        subscription.current_period_end = datetime.utcnow() + timedelta(days=30)

                        # Update company plan and workspace limits
                        company.plan = payment.plan  # Update company plan
                        plan_config = current_app.config.get('PLANS', {}).get(payment.plan, {})
                        if plan_config:
                            company.max_workspaces = plan_config.get('max_workspaces', 1)
                            logger.info(f"Updated company {company.id} to {payment.plan} plan with max_workspaces={company.max_workspaces}")

                            # Upgrade existing workspace storage to new plan limits
                            self._upgrade_workspace_storage(company, payment.plan)
                    else:
                        # Renewal payment - check if plan changed (upgrade/downgrade)
                        if subscription.plan != payment.plan:
                            logger.info(f"Plan change detected: {subscription.plan} -> {payment.plan}")
                            subscription.plan = payment.plan

                            # Update company plan and workspace limits for new plan
                            company.plan = payment.plan  # Update company plan
                            plan_config = current_app.config.get('PLANS', {}).get(payment.plan, {})
                            if plan_config:
                                company.max_workspaces = plan_config.get('max_workspaces', 1)
                                logger.info(f"Updated company {company.id} to {payment.plan} plan with max_workspaces={company.max_workspaces}")

                                # Upgrade existing workspace storage to new plan limits
                                self._upgrade_workspace_storage(company, payment.plan)

                        # Extend subscription period
                        subscription.current_period_start = subscription.current_period_end
                        subscription.current_period_end = subscription.current_period_end + timedelta(days=30)

                payment.subscription_id = subscription.id

                # Step 6: Generate invoice
                invoice = Invoice(
                    company_id=company.id,
                    payment_id=payment.id,
                    invoice_number=self._generate_invoice_number(),
                    subtotal=payment.amount,
                    tax_amount=0,
                    total_amount=payment.amount,
                    currency=payment.currency,
                    period_start=subscription.current_period_start,
                    period_end=subscription.current_period_end,
                    invoice_date=datetime.utcnow(),
                    due_date=datetime.utcnow(),
                    paid_at=datetime.utcnow(),
                    status='paid',
                    description=f"{company.plan.title()} Plan - Monthly Subscription"
                )
                db.session.add(invoice)

                db.session.commit()

                logger.info(f"Subscription activated for company {company.id}, "
                           f"invoice {invoice.invoice_number} generated")

                # Send success email notification to company admin
                try:
                    from app.services.email_service import send_payment_success_email
                    admin_user = company.users.filter_by(role='admin').first()
                    if admin_user:
                        send_payment_success_email(admin_user, payment, invoice, subscription)
                        logger.info(f"Payment success email sent to {admin_user.email}")
                except Exception as email_error:
                    # Log email failure but don't fail the payment processing
                    logger.error(f"Failed to send payment success email: {str(email_error)}")

                return True, "OK"

            else:
                # Payment failed
                payment.status = 'failed'
                payment.failure_reason_code = failed_reason_code
                payment.failure_reason_message = failed_reason_msg
                db.session.commit()

                logger.warning(f"Payment {payment.id} failed: {failed_reason_msg}")

                # Send failure email notification to company admin
                try:
                    from app.services.email_service import send_payment_failed_email
                    admin_user = company.users.filter_by(role='admin').first()
                    if admin_user:
                        send_payment_failed_email(admin_user, payment)
                        logger.info(f"Payment failure email sent to {admin_user.email}")
                except Exception as email_error:
                    # Log email failure but don't fail the payment processing
                    logger.error(f"Failed to send payment failure email: {str(email_error)}")

                return True, "OK"  # Still return OK to PayTR to acknowledge receipt

        except Exception as e:
            logger.error(f"Error processing payment callback: {str(e)}", exc_info=True)
            db.session.rollback()
            return False, f"Processing error: {str(e)}"

    def create_trial_subscription(self, company: Company, plan: str) -> Subscription:
        """
        Create a trial subscription for a new company.

        Args:
            company: Company model instance
            plan: Plan tier (starter, team, enterprise)

        Returns:
            Subscription: Created subscription record

        Side Effects:
            - Creates Subscription record with 14-day trial
            - Updates Company plan and max_workspaces
            - Commits changes to database
        """
        try:
            # Get plan configuration
            plans = current_app.config.get('PLANS', {})
            plan_config = plans.get(plan)

            if not plan_config:
                raise ValueError(f"Invalid plan: {plan}")

            # Calculate trial period
            trial_days = current_app.config.get('TRIAL_DAYS', 14)
            trial_starts = datetime.utcnow()
            trial_ends = trial_starts + timedelta(days=trial_days)

            # Create subscription
            subscription = Subscription(
                company_id=company.id,
                plan=plan,
                status='trial',
                trial_starts_at=trial_starts,
                trial_ends_at=trial_ends
            )

            # Update company
            company.plan = plan
            company.max_workspaces = plan_config['workspaces']

            db.session.add(subscription)
            db.session.commit()

            logger.info(f"Trial subscription created for company {company.id}, "
                       f"plan {plan}, expires {trial_ends}")

            return subscription

        except Exception as e:
            logger.error(f"Error creating trial subscription: {str(e)}", exc_info=True)
            db.session.rollback()
            raise

    def cancel_subscription(self, subscription: Subscription, immediate: bool = False) -> bool:
        """
        Cancel a subscription.

        Args:
            subscription: Subscription model instance to cancel
            immediate: If True, cancel immediately. If False, cancel at period end.

        Returns:
            bool: True if cancellation successful

        Side Effects:
            - Updates Subscription status
            - Sets cancellation flags
            - Commits changes to database
        """
        try:
            if immediate:
                subscription.status = 'cancelled'
                subscription.cancelled_at = datetime.utcnow()
                logger.info(f"Subscription {subscription.id} cancelled immediately")
            else:
                subscription.cancel_at_period_end = True
                subscription.cancelled_at = datetime.utcnow()
                logger.info(f"Subscription {subscription.id} will cancel at period end")

            db.session.commit()
            return True

        except Exception as e:
            logger.error(f"Error cancelling subscription: {str(e)}", exc_info=True)
            db.session.rollback()
            return False

    def _upgrade_workspace_storage(self, company: Company, new_plan: str) -> None:
        """
        Upgrade all company workspaces to new plan storage quota.

        Args:
            company: Company model instance
            new_plan: New plan tier (starter, team, enterprise)

        Side Effects:
            - Updates workspace disk_quota_gb in database
            - Logs storage upgrade for each workspace
        """
        try:
            # Get new plan storage quota
            plan_config = current_app.config.get('PLANS', {}).get(new_plan, {})
            new_storage_quota = plan_config.get('storage_per_workspace_gb', 10)

            # Get all company workspaces
            workspaces = Workspace.query.filter_by(company_id=company.id).all()

            provisioner = WorkspaceProvisioner()
            upgraded_count = 0

            for workspace in workspaces:
                # Only upgrade if new quota is higher
                if workspace.disk_quota_gb < new_storage_quota:
                    try:
                        result = provisioner.resize_workspace_disk(workspace, new_storage_quota)
                        if result.get('success'):
                            upgraded_count += 1
                            logger.info(
                                f"Upgraded workspace {workspace.id} ({workspace.name}) "
                                f"from {result['old_quota_gb']}GB to {new_storage_quota}GB"
                            )
                    except Exception as e:
                        logger.error(
                            f"Failed to upgrade workspace {workspace.id}: {str(e)}"
                        )

            if upgraded_count > 0:
                logger.info(
                    f"Plan upgrade storage: upgraded {upgraded_count} workspaces "
                    f"for company {company.id} to {new_storage_quota}GB"
                )

        except Exception as e:
            logger.error(f"Error in _upgrade_workspace_storage: {str(e)}", exc_info=True)

    def _generate_invoice_number(self) -> str:
        """
        Generate unique invoice number in format INV-YYYY-NNNNN.

        Returns:
            str: Unique invoice number
        """
        year = datetime.utcnow().year
        count = Invoice.query.filter(
            Invoice.invoice_number.like(f'INV-{year}-%')
        ).count()
        return f'INV-{year}-{count + 1:05d}'
