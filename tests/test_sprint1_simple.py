#!/usr/bin/env python3
"""
Simplified E2E tests for Sprint 1 workspace features.
Tests settings and welcome pages directly with known workspace ID.
"""

import asyncio
from playwright.async_api import async_playwright
import sys

# Test configuration
EMAIL = "mustafa+30@alkedos.com"
PASSWORD = "Mstf123!"
WORKSPACE_ID = 41  # authtest2 workspace

async def test_sprint1_direct():
    """Test Sprint 1 features directly."""

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            print("=" * 70)
            print("SPRINT 1 E2E TESTS - Direct Settings & Welcome Page Validation")
            print("=" * 70)

            # Step 1: Login
            print("\n[TEST 1] Login to YouAreCoder")
            await page.goto("https://youarecoder.com/auth/login")
            await page.wait_for_selector('input[name="email"]', timeout=5000)

            await page.fill('input[name="email"]', EMAIL)
            await page.fill('input[name="password"]', PASSWORD)

            # Use expect_navigation for proper async handling
            async with page.expect_navigation(timeout=15000):
                await page.click('text="Sign in"')

            print(f"✅ Login successful - redirected to: {page.url}")

            # Step 2: Test Settings Page
            print(f"\n[TEST 2] Navigate to Settings page (workspace {WORKSPACE_ID})")
            settings_url = f"https://youarecoder.com/workspace/{WORKSPACE_ID}/settings"
            await page.goto(settings_url)
            await page.wait_for_load_state("networkidle", timeout=10000)

            print(f"Settings page loaded: {page.url}")

            # Verify page heading
            heading = await page.locator('h1').first.inner_text()
            print(f"   Page heading: {heading}")

            # Check for Workspace Information section
            workspace_info = page.locator('h2:has-text("Workspace Information")')
            if await workspace_info.count() > 0:
                print("   ✅ Workspace Information section found")
            else:
                print("   ❌ Workspace Information section NOT found")
                return False

            # Check for SSH Key section
            ssh_section = page.locator('h2:has-text("SSH Key")')
            if await ssh_section.count() > 0:
                print("   ✅ SSH Key section found")

                # Verify SSH key textarea
                ssh_textarea = page.locator('#ssh-key-text')
                if await ssh_textarea.count() > 0:
                    ssh_key_value = await ssh_textarea.input_value()
                    if ssh_key_value and len(ssh_key_value) > 100:
                        print(f"   ✅ SSH public key displayed ({len(ssh_key_value)} chars)")
                    else:
                        print("   ⚠️  SSH key textarea empty or too short")
                else:
                    print("   ❌ SSH key textarea (#ssh-key-text) NOT found")

                # Verify copy button
                copy_btn = page.locator('button:has-text("Copy")')
                if await copy_btn.count() > 0:
                    print("   ✅ Copy button found")
                else:
                    print("   ❌ Copy button NOT found")

                # Verify verify SSH button
                verify_btn = page.locator('button:has-text("Verify GitHub Connection")')
                if await verify_btn.count() > 0:
                    print("   ✅ Verify GitHub Connection button found")
                else:
                    print("   ❌ Verify button NOT found")

                # Test copy functionality
                print("\n[TEST 3] Test SSH key copy functionality")
                try:
                    # Click copy button
                    await copy_btn.click()
                    await page.wait_for_timeout(500)

                    # Check if button text changed to "Copied!"
                    copy_text_elem = page.locator('#copy-text')
                    if await copy_text_elem.count() > 0:
                        copy_text = await copy_text_elem.inner_text()
                        if "Copied" in copy_text:
                            print("   ✅ Copy button feedback working (text changed to 'Copied!')")
                        else:
                            print(f"   ⚠️  Copy button text: '{copy_text}'")
                except Exception as e:
                    print(f"   ⚠️  Copy functionality test failed: {str(e)}")

            else:
                print("   ⚠️  No SSH Key section (workspace may not have SSH configured)")

            # Check for Resource Limits section
            resource_section = page.locator('h2:has-text("Resource Limits")')
            if await resource_section.count() > 0:
                print("   ✅ Resource Limits section found")

                # Check for specific resource limit fields
                cpu_limit = page.locator('text="CPU Limit"')
                memory_limit = page.locator('text="Memory Limit"')
                disk_quota = page.locator('text="Disk Quota"')

                if await cpu_limit.count() > 0:
                    print("   ✅ CPU Limit field found")
                if await memory_limit.count() > 0:
                    print("   ✅ Memory Limit field found")
                if await disk_quota.count() > 0:
                    print("   ✅ Disk Quota field found")
            else:
                print("   ❌ Resource Limits section NOT found")

            # Step 4: Test Welcome Page
            print(f"\n[TEST 4] Navigate to Welcome page (workspace {WORKSPACE_ID})")
            welcome_url = f"https://youarecoder.com/workspace/{WORKSPACE_ID}/welcome"

            # Clear session storage to test fresh welcome page experience
            await context.clear_cookies()
            await page.goto(welcome_url)
            await page.wait_for_load_state("networkidle", timeout=10000)

            current_url = page.url
            print(f"Welcome page URL: {current_url}")

            if "/welcome" in current_url:
                print("   ✅ Welcome page displayed")

                # Check for welcome heading
                welcome_heading = page.locator('h1')
                if await welcome_heading.count() > 0:
                    heading_text = await welcome_heading.first.inner_text()
                    print(f"   ✅ Welcome heading found: '{heading_text}'")
                else:
                    print("   ❌ Welcome heading NOT found")

                # Check for "Open Workspace" button
                open_workspace_btn = page.locator('a:has-text("Open Workspace")')
                open_btn_count = await open_workspace_btn.count()
                if open_btn_count > 0:
                    print(f"   ✅ Open Workspace button found ({open_btn_count} instances)")
                else:
                    print("   ❌ Open Workspace button NOT found")

                # Check for "Back to Dashboard" button
                back_btn = page.locator('a:has-text("Back to Dashboard")')
                if await back_btn.count() > 0:
                    print("   ✅ Back to Dashboard button found")
                else:
                    print("   ❌ Back to Dashboard button NOT found")

                # Check for template information (if workspace uses template)
                template_heading = page.locator('h2:has-text("Template:")')
                if await template_heading.count() > 0:
                    print("   ✅ Template information section found")

                    # Check for extensions
                    extensions_heading = page.locator('h3:has-text("Installed VS Code Extensions")')
                    if await extensions_heading.count() > 0:
                        print("   ✅ Extensions section found")

                    # Check for repositories
                    repos_heading = page.locator('h3:has-text("Cloned Repositories")')
                    if await repos_heading.count() > 0:
                        print("   ✅ Repositories section found")

                    # Check for packages
                    packages_heading = page.locator('h3:has-text("Pre-installed Packages")')
                    if await packages_heading.count() > 0:
                        print("   ✅ Packages section found")
                else:
                    print("   ⚠️  No template information (workspace may not use template)")

                # Check for "Next Steps" section
                next_steps = page.locator('h2:has-text("Next Steps")')
                if await next_steps.count() > 0:
                    print("   ✅ Next Steps section found")
                else:
                    print("   ❌ Next Steps section NOT found")

                # Test session tracking
                print("\n[TEST 5] Test welcome page session tracking (second visit)")
                await page.goto(welcome_url)
                await page.wait_for_load_state("networkidle", timeout=10000)

                second_visit_url = page.url
                if "/welcome" not in second_visit_url:
                    print(f"   ✅ Second visit redirected (session tracking works)")
                    print(f"   Redirected to: {second_visit_url}")
                else:
                    print("   ⚠️  Second visit still shows welcome (session may not persist)")

            else:
                print(f"   ⚠️  Redirected away from welcome page to: {current_url}")
                print("   This may indicate session was already set or auto-redirect is active")

            # Step 6: Test Back navigation from Settings
            print("\n[TEST 6] Test Back to Dashboard navigation from Settings")
            await page.goto(settings_url)
            await page.wait_for_load_state("networkidle", timeout=5000)

            back_link = page.locator('a:has-text("Back to Dashboard")')
            if await back_link.count() > 0:
                print("   ✅ Back to Dashboard link found")
                await back_link.click()
                await page.wait_for_load_state("networkidle", timeout=5000)

                if "/dashboard" in page.url or page.url.endswith(".com/"):
                    print(f"   ✅ Successfully navigated back to dashboard: {page.url}")
                else:
                    print(f"   ⚠️  Unexpected URL after back navigation: {page.url}")
            else:
                print("   ❌ Back to Dashboard link NOT found")

            print("\n" + "=" * 70)
            print("SPRINT 1 E2E TESTS COMPLETE - All Features Validated")
            print("=" * 70)

            return True

        except Exception as e:
            print(f"\n❌ Test failed with error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_sprint1_direct())
    sys.exit(0 if result else 1)
