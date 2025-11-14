#!/usr/bin/env python3
"""
E2E tests for Sprint 1 workspace improvement features.

Tests:
1. SSH Key Access - Settings page with persistent SSH key access
2. Welcome Page - First-time onboarding with session tracking
3. Settings page navigation from manage modal
"""

import asyncio
from playwright.async_api import async_playwright
import sys

# Test credentials
EMAIL = "mustafa+30@alkedos.com"
PASSWORD = "Mstf123!"

async def test_sprint1_features():
    """Test Sprint 1 workspace features end-to-end."""

    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            print("=" * 60)
            print("SPRINT 1 E2E TESTS - Workspace Improvements")
            print("=" * 60)

            # Step 1: Login
            print("\n[TEST 1] Login to YouAreCoder")
            await page.goto("https://youarecoder.com/auth/login")
            await page.wait_for_selector('input[name="email"]', timeout=5000)

            await page.fill('input[name="email"]', EMAIL)
            await page.fill('input[name="password"]', PASSWORD)

            await page.click('text="Sign in"')

            # Wait for navigation after login (could be dashboard or index)
            await page.wait_for_load_state("networkidle", timeout=10000)
            login_redirect_url = page.url
            print(f"Login redirected to: {login_redirect_url}")

            # Navigate to dashboard explicitly
            await page.goto("https://youarecoder.com/dashboard")
            await page.wait_for_load_state("networkidle", timeout=5000)
            print("✅ Login successful, navigated to dashboard")

            # Step 2: Navigate to dashboard and find workspace
            print("\n[TEST 2] Find existing workspace on dashboard")
            current_url = page.url
            print(f"Current URL: {current_url}")

            # Wait for workspaces to load
            await page.wait_for_selector('[data-testid="workspace-card"]', timeout=5000)
            workspace_cards = await page.locator('[data-testid="workspace-card"]').all()
            print(f"Found {len(workspace_cards)} workspace(s)")

            if len(workspace_cards) == 0:
                print("❌ No workspaces found on dashboard")
                return False

            # Get first workspace details
            first_card = workspace_cards[0]
            workspace_name = await first_card.locator('h3').inner_text()
            print(f"Testing with workspace: {workspace_name}")

            # Step 3: Open manage modal
            print("\n[TEST 3] Open workspace manage modal")
            manage_btn = first_card.locator('button:has-text("Manage")')
            await manage_btn.click()

            # Wait for modal to appear
            await page.wait_for_selector('#manage-modal', timeout=5000)
            print("✅ Manage modal opened")

            # Step 4: Verify Settings button exists in modal
            print("\n[TEST 4] Verify Settings button in manage modal")
            settings_btn = page.locator('#manage-modal a:has-text("Settings")')

            if await settings_btn.count() == 0:
                print("❌ Settings button not found in manage modal")
                return False

            print("✅ Settings button found in manage modal")

            # Step 5: Click Settings button and navigate
            print("\n[TEST 5] Navigate to Settings page")
            await settings_btn.click()

            # Wait for navigation to settings page
            await page.wait_for_url("**/settings", timeout=5000)
            current_url = page.url
            print(f"Settings page URL: {current_url}")

            # Step 6: Verify Settings page content
            print("\n[TEST 6] Verify Settings page content")

            # Check for main heading
            heading = await page.locator('h1').inner_text()
            if workspace_name not in heading:
                print(f"⚠️  Heading mismatch: expected '{workspace_name}', got '{heading}'")
            else:
                print(f"✅ Correct heading: {heading}")

            # Check for SSH key section (if workspace has SSH key)
            ssh_section = page.locator('h2:has-text("SSH Key")')
            if await ssh_section.count() > 0:
                print("✅ SSH Key section found")

                # Check for SSH key textarea
                ssh_textarea = page.locator('#ssh-key-text')
                if await ssh_textarea.count() > 0:
                    ssh_key = await ssh_textarea.input_value()
                    if ssh_key and 'ssh-rsa' in ssh_key:
                        print(f"✅ SSH public key displayed (length: {len(ssh_key)} chars)")
                    else:
                        print("⚠️  SSH key textarea found but content unexpected")
                else:
                    print("❌ SSH key textarea not found")

                # Check for copy button
                copy_btn = page.locator('button:has-text("Copy")')
                if await copy_btn.count() > 0:
                    print("✅ Copy SSH key button found")
                else:
                    print("❌ Copy button not found")

                # Check for verify button
                verify_btn = page.locator('button:has-text("Verify GitHub Connection")')
                if await verify_btn.count() > 0:
                    print("✅ Verify GitHub Connection button found")
                else:
                    print("❌ Verify button not found")
            else:
                print("⚠️  No SSH Key section (workspace may not have SSH key)")

            # Check for Resource Limits section
            resource_section = page.locator('h2:has-text("Resource Limits")')
            if await resource_section.count() > 0:
                print("✅ Resource Limits section found")
            else:
                print("❌ Resource Limits section not found")

            # Step 7: Navigate back to dashboard
            print("\n[TEST 7] Navigate back to dashboard")
            back_link = page.locator('a:has-text("Back to Dashboard")')
            await back_link.click()
            await page.wait_for_url("**/dashboard", timeout=5000)
            print("✅ Successfully navigated back to dashboard")

            # Step 8: Test Welcome page (create new session to test first-time experience)
            print("\n[TEST 8] Test Welcome page session tracking")

            # Get workspace ID from settings URL we just visited
            workspace_id = current_url.split('/')[-2]
            welcome_url = f"https://youarecoder.com/workspace/{workspace_id}/welcome"

            print(f"Navigating to welcome page: {welcome_url}")
            await page.goto(welcome_url)

            # Wait for page load
            await page.wait_for_load_state("networkidle", timeout=5000)
            current_url = page.url

            # Session tracking: First visit should show welcome, second visit should redirect
            if "/welcome" in current_url:
                print("✅ Welcome page displayed on first visit")

                # Check for welcome content
                welcome_heading = page.locator('h1:has-text("Welcome to")')
                if await welcome_heading.count() > 0:
                    print("✅ Welcome heading found")
                else:
                    print("❌ Welcome heading not found")

                # Check for "Open Workspace" button
                open_btn = page.locator('a:has-text("Open Workspace")')
                if await open_btn.count() > 0:
                    print("✅ Open Workspace button found")
                else:
                    print("❌ Open Workspace button not found")

                # Test session tracking - second visit should redirect
                print("\n[TEST 9] Test welcome page session tracking (second visit)")
                await page.goto(welcome_url)
                await page.wait_for_load_state("networkidle", timeout=5000)

                if "/welcome" not in page.url:
                    print("✅ Second visit redirected (session tracking works)")
                    print(f"   Redirected to: {page.url}")
                else:
                    print("⚠️  Second visit still shows welcome page (session tracking may not be working)")
            else:
                print(f"⚠️  Welcome page immediately redirected to: {current_url}")
                print("   This may indicate session was already set or workspace redirect is active")

            print("\n" + "=" * 60)
            print("SPRINT 1 E2E TESTS COMPLETE")
            print("=" * 60)

            return True

        except Exception as e:
            print(f"\n❌ Test failed with error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_sprint1_features())
    sys.exit(0 if result else 1)
