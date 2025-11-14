#!/usr/bin/env python3
"""
Test HTMX workspace creation with detailed logging
"""
import random
import string
import time
from playwright.sync_api import sync_playwright

def generate_random_id(length=6):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def test_htmx_workspace():
    random_id = generate_random_id()

    test_data = {
        'company_name': f'HTMX Test Company {random_id}',
        'subdomain': f'htmxtest{random_id}',
        'full_name': 'Mustafa Kördönmez',
        'username': f'mustafa{random_id}',
        'email': f'mustafa+10@alkedos.com',
        'password': 'CompleteTest123!@#',
        'workspace_name': f'htmx-ws-{random_id}'
    }

    print("=" * 80)
    print("🧪 HTMX WORKSPACE TEST")
    print("=" * 80)
    print(f"Email: {test_data['email']}")
    print(f"Subdomain: {test_data['subdomain']}")
    print(f"Workspace: {test_data['workspace_name']}")
    print()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=500)  # Visible browser with slow motion
        context = browser.new_context(viewport={'width': 1280, 'height': 720})
        page = context.new_page()

        # Enable request/response logging
        page.on("request", lambda request: print(f"→ {request.method} {request.url}"))
        page.on("response", lambda response: print(f"← {response.status} {response.url}"))

        try:
            # STEP 1: REGISTRATION
            print("\n📝 STEP 1: Registration")
            page.goto('https://youarecoder.com/auth/register', timeout=30000)

            page.fill('input[name="company_name"]', test_data['company_name'])
            page.fill('input[name="subdomain"]', test_data['subdomain'])
            page.fill('input[name="full_name"]', test_data['full_name'])
            page.fill('input[name="username"]', test_data['username'])
            page.fill('input[name="email"]', test_data['email'])
            page.fill('input[name="password"]', test_data['password'])
            page.fill('input[name="password_confirm"]', test_data['password'])

            page.click('input[type="submit"]')
            page.wait_for_url('**/auth/login', timeout=30000)
            print("✅ Registration successful")

            # STEP 2: LOGIN
            print("\n🔐 STEP 2: Login")
            time.sleep(2)

            subdomain_url = f"https://{test_data['subdomain']}.youarecoder.com/auth/login"
            page.goto(subdomain_url, timeout=30000)

            page.fill('input[name="email"]', test_data['email'])
            page.fill('input[name="password"]', test_data['password'])
            page.click('input[type="submit"]')
            page.wait_for_url('**/dashboard', timeout=30000)
            print("✅ Login successful")

            # STEP 3: CREATE WORKSPACE
            print("\n📦 STEP 3: Create Workspace (HTMX)")

            # Take screenshot before clicking
            page.screenshot(path=f"/tmp/before_click_{random_id}.png")
            print("📸 Screenshot before: /tmp/before_click_{random_id}.png")

            # Click "New Workspace" link
            print("Clicking 'New Workspace' link...")
            page.click('a:has-text("New Workspace")')
            time.sleep(1)

            # Take screenshot after modal opens
            page.screenshot(path=f"/tmp/modal_open_{random_id}.png")
            print("📸 Screenshot modal open: /tmp/modal_open_{random_id}.png")

            # Fill workspace name
            print(f"Filling workspace name: {test_data['workspace_name']}")
            page.wait_for_selector('input[name="name"]', timeout=5000)
            page.fill('input[name="name"]', test_data['workspace_name'])

            # Take screenshot before submit
            page.screenshot(path=f"/tmp/before_submit_{random_id}.png")
            print("📸 Screenshot before submit: /tmp/before_submit_{random_id}.png")

            # Submit form
            print("Clicking submit button...")
            page.click('input[type="submit"]')

            # Wait and observe
            print("⏳ Waiting 10 seconds to observe behavior...")
            time.sleep(10)

            # Take screenshot after submit
            page.screenshot(path=f"/tmp/after_submit_{random_id}.png", full_page=True)
            print("📸 Screenshot after submit: /tmp/after_submit_{random_id}.png")

            # Check current URL
            current_url = page.url
            print(f"\n📍 Current URL: {current_url}")

            # Check if redirected to dashboard
            if '/dashboard' in current_url:
                print("✅ Successfully redirected to dashboard!")
            elif '/workspace/create' in current_url:
                print("❌ PROBLEM: Still on /workspace/create page")
                print("   This means HTMX redirect is not working")
            else:
                print(f"⚠️  Unexpected URL: {current_url}")

            # Check for flash messages
            try:
                flash_message = page.locator('.bg-green-50, .bg-red-50').first
                if flash_message.is_visible():
                    message_text = flash_message.text_content()
                    print(f"💬 Flash message: {message_text}")
            except:
                print("📭 No flash messages found")

            print("\n" + "=" * 80)
            print("TEST COMPLETED - Check screenshots above")
            print("=" * 80)

            # Keep browser open for inspection
            

        except Exception as e:
            print(f"\n❌ ERROR: {str(e)}")
            page.screenshot(path=f"/tmp/error_{random_id}.png")
            print(f"📸 Error screenshot: /tmp/error_{random_id}.png")
            raise

        finally:
            browser.close()

if __name__ == '__main__':
    test_htmx_workspace()
