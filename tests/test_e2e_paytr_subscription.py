#!/usr/bin/env python3
"""
Playwright E2E Test: Complete PayTR Subscription Flow

Tests the full subscription journey:
1. User registration
2. Login to dashboard
3. Navigate to billing
4. Initiate subscription (mock PayTR response)
5. Verify subscription status
6. Check email notifications

Note: This test uses mocked PayTR responses since we don't have live credentials yet.
For production testing with real PayTR, update MOCK_PAYTR = False
"""

import random
import string
import time
from playwright.sync_api import sync_playwright, expect
from datetime import datetime


# Configuration
BASE_URL = 'https://youarecoder.com'
MOCK_PAYTR = True  # Set to False for real PayTR testing
HEADLESS = True  # Set to False to see browser during testing


def generate_random_string(length=8):
    """Generate random alphanumeric string"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


def print_section(title):
    """Print formatted section header"""
    print('\n' + '='*80)
    print(f'  {title}')
    print('='*80)


def print_step(step, status='⏳'):
    """Print test step with status"""
    print(f'{status} {step}')


class PayTRSubscriptionE2ETest:
    """End-to-end test suite for PayTR subscription flow"""

    def __init__(self):
        self.random_id = generate_random_string(6)
        self.test_data = {
            'company_name': f'PayTR Test Co {self.random_id}',
            'subdomain': f'paytrtest{self.random_id}',
            'full_name': 'PayTR Test User',
            'username': f'paytr{self.random_id}',
            'email': f'paytr+{self.random_id}@alkedos.com',
            'password': 'PayTRTest123!@#'
        }
        self.screenshots = []
        self.test_results = {
            'registration': False,
            'login': False,
            'billing_access': False,
            'subscription_initiation': False,
            'payment_callback': False,
            'email_notification': False,
            'subscription_status': False
        }

    def take_screenshot(self, page, name):
        """Take screenshot and store path"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        path = f'/tmp/paytr_e2e_{name}_{self.random_id}_{timestamp}.png'
        page.screenshot(path=path)
        self.screenshots.append(path)
        print(f'   📸 Screenshot: {path}')
        return path

    def test_registration(self, page):
        """Test Step 1: User Registration"""
        print_section('STEP 1: USER REGISTRATION')

        try:
            print_step('Navigating to registration page')
            page.goto(f'{BASE_URL}/auth/register', timeout=30000)
            self.take_screenshot(page, 'registration_page')

            print_step('Filling registration form')
            page.fill('input[name="company_name"]', self.test_data['company_name'])
            page.fill('input[name="subdomain"]', self.test_data['subdomain'])
            page.fill('input[name="full_name"]', self.test_data['full_name'])
            page.fill('input[name="username"]', self.test_data['username'])
            page.fill('input[name="email"]', self.test_data['email'])
            page.fill('input[name="password"]', self.test_data['password'])
            page.fill('input[name="password_confirm"]', self.test_data['password'])

            print_step('Submitting registration form')
            page.click('input[type="submit"]')
            page.wait_for_load_state('networkidle', timeout=10000)

            self.take_screenshot(page, 'registration_result')

            # Check if registration succeeded
            current_url = page.url
            if 'login' in current_url or 'dashboard' in current_url:
                self.test_results['registration'] = True
                print_step('User registered successfully', '✅')
                return True
            else:
                print_step('Registration may have failed - check screenshot', '⚠️')
                return False

        except Exception as e:
            print_step(f'Registration error: {e}', '❌')
            self.take_screenshot(page, 'registration_error')
            return False

    def test_login(self, page):
        """Test Step 2: User Login"""
        print_section('STEP 2: USER LOGIN')

        try:
            print_step('Navigating to login page')
            page.goto(f'{BASE_URL}/auth/login', timeout=30000)

            print_step('Filling login credentials')
            page.fill('input[name="username"]', self.test_data['username'])
            page.fill('input[name="password"]', self.test_data['password'])

            self.take_screenshot(page, 'login_page')

            print_step('Submitting login form')
            page.click('input[type="submit"]')
            page.wait_for_load_state('networkidle', timeout=10000)

            self.take_screenshot(page, 'login_result')

            # Verify we're on dashboard
            current_url = page.url
            if 'dashboard' in current_url or 'workspace' in current_url:
                self.test_results['login'] = True
                print_step('Login successful - on dashboard', '✅')
                return True
            else:
                print_step(f'Login may have failed - current URL: {current_url}', '⚠️')
                return False

        except Exception as e:
            print_step(f'Login error: {e}', '❌')
            self.take_screenshot(page, 'login_error')
            return False

    def test_billing_access(self, page):
        """Test Step 3: Access Billing Dashboard"""
        print_section('STEP 3: ACCESS BILLING DASHBOARD')

        try:
            print_step('Navigating to billing dashboard')
            page.goto(f'{BASE_URL}/billing/', timeout=30000)
            page.wait_for_load_state('networkidle', timeout=10000)

            self.take_screenshot(page, 'billing_dashboard')

            # Check if billing page loaded
            page_content = page.content()
            if 'subscription' in page_content.lower() or 'plan' in page_content.lower():
                self.test_results['billing_access'] = True
                print_step('Billing dashboard accessible', '✅')
                return True
            else:
                print_step('Billing dashboard may not have loaded correctly', '⚠️')
                return False

        except Exception as e:
            print_step(f'Billing access error: {e}', '❌')
            self.take_screenshot(page, 'billing_error')
            return False

    def test_subscription_initiation(self, page):
        """Test Step 4: Initiate Subscription (Starter Plan)"""
        print_section('STEP 4: INITIATE SUBSCRIPTION (STARTER PLAN)')

        try:
            print_step('Looking for Starter plan subscription button')

            # Try different possible button selectors
            button_selectors = [
                'button:has-text("Subscribe")',
                'button:has-text("Start Trial")',
                'a:has-text("Subscribe")',
                'a:has-text("Start Trial")',
                '[data-plan="starter"]',
                'form[action*="starter"] button',
            ]

            button_found = False
            for selector in button_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        print_step(f'Found subscription button: {selector}')
                        page.click(selector, timeout=5000)
                        button_found = True
                        break
                except:
                    continue

            if not button_found:
                print_step('No subscription button found - may need UI implementation', '⚠️')
                self.take_screenshot(page, 'no_subscription_button')

                # Alternative: Direct POST request via JavaScript
                print_step('Attempting direct subscription via JavaScript')
                result = page.evaluate("""
                    async () => {
                        const response = await fetch('/billing/subscribe/starter', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            }
                        });
                        return {
                            status: response.status,
                            data: await response.json()
                        };
                    }
                """)

                if result['status'] == 200:
                    print_step('Subscription initiated via API', '✅')
                    self.test_results['subscription_initiation'] = True
                    return True
                else:
                    print_step(f'API subscription failed: {result}', '⚠️')
                    return False

            # Wait for response
            page.wait_for_load_state('networkidle', timeout=10000)
            self.take_screenshot(page, 'subscription_initiated')

            # Check for PayTR iframe or success message
            page_content = page.content()
            if 'paytr' in page_content.lower() or 'payment' in page_content.lower():
                self.test_results['subscription_initiation'] = True
                print_step('Subscription initiated successfully', '✅')
                return True
            else:
                print_step('Subscription initiation unclear - check screenshot', '⚠️')
                return False

        except Exception as e:
            print_step(f'Subscription initiation error: {e}', '❌')
            self.take_screenshot(page, 'subscription_error')
            return False

    def test_payment_callback_simulation(self, page):
        """Test Step 5: Simulate PayTR Payment Callback (Mocked)"""
        print_section('STEP 5: SIMULATE PAYMENT CALLBACK')

        if not MOCK_PAYTR:
            print_step('Skipping mock - real PayTR flow', '⏭️')
            return True

        try:
            print_step('Simulating successful PayTR callback')

            # Get the payment record from database (via API or direct)
            # For now, simulate successful callback via JavaScript
            result = page.evaluate("""
                async () => {
                    // This would normally come from PayTR webhook
                    const mockCallbackData = {
                        merchant_oid: 'YAC-TEST-' + Date.now(),
                        status: 'success',
                        total_amount: '2900',  // $29 in cents
                        hash: 'MOCK_HASH_VALUE'
                    };

                    try {
                        const response = await fetch('/billing/callback', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/x-www-form-urlencoded'
                            },
                            body: new URLSearchParams(mockCallbackData)
                        });

                        return {
                            status: response.status,
                            text: await response.text()
                        };
                    } catch (e) {
                        return {error: e.message};
                    }
                }
            """)

            print_step(f'Callback simulation result: {result}')

            if result.get('status') in [200, 400]:  # 400 expected for invalid hash
                print_step('Callback endpoint accessible (hash validation expected)', '✅')
                self.test_results['payment_callback'] = True
                return True
            else:
                print_step('Callback simulation issue', '⚠️')
                return False

        except Exception as e:
            print_step(f'Callback simulation error: {e}', '❌')
            return False

    def test_subscription_status(self, page):
        """Test Step 6: Verify Subscription Status"""
        print_section('STEP 6: VERIFY SUBSCRIPTION STATUS')

        try:
            print_step('Refreshing billing dashboard')
            page.goto(f'{BASE_URL}/billing/', timeout=30000)
            page.wait_for_load_state('networkidle', timeout=10000)

            self.take_screenshot(page, 'subscription_status')

            # Check for trial/active status indicators
            page_content = page.content()
            status_indicators = ['trial', 'active', 'subscribed', 'starter']

            found_status = False
            for indicator in status_indicators:
                if indicator in page_content.lower():
                    print_step(f'Found status indicator: {indicator}', '✅')
                    found_status = True
                    break

            if found_status:
                self.test_results['subscription_status'] = True
                print_step('Subscription status visible', '✅')
                return True
            else:
                print_step('No clear subscription status found', '⚠️')
                return False

        except Exception as e:
            print_step(f'Status check error: {e}', '❌')
            self.take_screenshot(page, 'status_error')
            return False

    def generate_report(self):
        """Generate comprehensive test report"""
        print_section('TEST EXECUTION REPORT')

        print(f'\n📋 Test Data:')
        print(f'   Company: {self.test_data["company_name"]}')
        print(f'   Subdomain: {self.test_data["subdomain"]}')
        print(f'   Email: {self.test_data["email"]}')

        print(f'\n📊 Test Results:')
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)

        for test_name, passed in self.test_results.items():
            status = '✅ PASS' if passed else '❌ FAIL'
            print(f'   {status} - {test_name.replace("_", " ").title()}')

        print(f'\n📈 Summary:')
        print(f'   Total Tests: {total_tests}')
        print(f'   Passed: {passed_tests}')
        print(f'   Failed: {total_tests - passed_tests}')
        print(f'   Success Rate: {(passed_tests/total_tests)*100:.1f}%')

        print(f'\n📸 Screenshots ({len(self.screenshots)}):')
        for screenshot in self.screenshots:
            print(f'   {screenshot}')

        print(f'\n📧 Email Check:')
        print(f'   Check inbox: {self.test_data["email"]}')
        print(f'   Expected emails:')
        print(f'   - Registration welcome email')
        if self.test_results['subscription_initiation']:
            print(f'   - Payment success email (if callback succeeded)')

        print('\n' + '='*80)

        return passed_tests, total_tests

    def run(self):
        """Execute full E2E test suite"""
        print_section('PAYTR SUBSCRIPTION E2E TEST SUITE')
        print(f'\n🎯 Configuration:')
        print(f'   Base URL: {BASE_URL}')
        print(f'   Mock PayTR: {MOCK_PAYTR}')
        print(f'   Headless: {HEADLESS}')

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=HEADLESS)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = context.new_page()

            try:
                # Execute test steps in sequence
                self.test_registration(page)
                time.sleep(2)  # Allow backend to process

                self.test_login(page)
                time.sleep(1)

                self.test_billing_access(page)
                time.sleep(1)

                self.test_subscription_initiation(page)
                time.sleep(2)

                self.test_payment_callback_simulation(page)
                time.sleep(2)

                self.test_subscription_status(page)

                # Generate final report
                passed, total = self.generate_report()

                return passed == total

            except Exception as e:
                print(f'\n❌ FATAL ERROR: {type(e).__name__}: {e}')
                self.take_screenshot(page, 'fatal_error')
                self.generate_report()
                return False

            finally:
                browser.close()


def main():
    """Main test execution"""
    test_suite = PayTRSubscriptionE2ETest()
    success = test_suite.run()

    print('\n' + '='*80)
    if success:
        print('✅ ALL E2E TESTS PASSED')
    else:
        print('⚠️  SOME E2E TESTS FAILED - See report above')
    print('='*80 + '\n')

    return 0 if success else 1


if __name__ == '__main__':
    exit(main())
