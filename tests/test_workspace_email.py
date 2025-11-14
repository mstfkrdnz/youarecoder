#!/usr/bin/env python3
"""
Playwright test: Login and create workspace to trigger workspace ready email
"""

import random
import string
from playwright.sync_api import sync_playwright

def generate_random_string(length=8):
    """Generate random alphanumeric string"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def test_workspace_creation_email():
    """Login and create workspace to test email system"""

    random_id = generate_random_string(6)
    test_data = {
        'email': 'mustafa@alkedos.com',
        'password': 'Qkdenz07!',  # Gerçek şifre
        'workspace_name': f'test-ws-{random_id}'
    }

    print('\n' + '='*80)
    print('🎭 PLAYWRIGHT WORKSPACE EMAIL TESTİ')
    print('='*80)
    print(f'\n📋 Test Verileri:')
    print(f'   Email: {test_data["email"]}')
    print(f'   Workspace: {test_data["workspace_name"]}')

    with sync_playwright() as p:
        print('\n🌐 Browser başlatılıyor...')
        browser = p.chromium.launch(headless=True)  # headless mode (no X server)
        context = browser.new_context()
        page = context.new_page()

        try:
            # Login
            print('\n📍 Login sayfasına gidiliyor...')
            page.goto('https://alkedos.youarecoder.com/auth/login', timeout=30000)
            print('   ✅ Sayfa yüklendi')

            print('\n🔐 Login yapılıyor...')
            page.fill('input[name="email"]', test_data['email'])
            page.fill('input[name="password"]', test_data['password'])

            # Click Sign in button (it's an input type="submit")
            page.click('input[type="submit"]')

            # Wait for dashboard
            print('   ⏳ Dashboard bekleniyor...')
            page.wait_for_load_state('networkidle', timeout=15000)

            current_url = page.url
            print(f'   📍 Mevcut URL: {current_url}')

            if 'dashboard' in current_url or 'workspaces' in current_url:
                print('   ✅ Login başarılı!')

                # Find and click create workspace button
                print('\n📦 Workspace oluşturuluyor...')

                # Try different selectors for create button
                create_button = None
                selectors = [
                    'button:has-text("Create Workspace")',
                    'a:has-text("Create Workspace")',
                    'button:has-text("New Workspace")',
                    'a:has-text("New Workspace")',
                    '[data-test="create-workspace"]'
                ]

                for selector in selectors:
                    try:
                        if page.locator(selector).count() > 0:
                            create_button = page.locator(selector).first
                            print(f'   ✅ Create button bulundu: {selector}')
                            break
                    except:
                        continue

                if create_button:
                    create_button.click()
                    print('   ✅ Create butonuna tıklandı')

                    page.wait_for_timeout(1000)

                    # Fill workspace name and press Enter
                    page.fill('input[name="name"]', test_data['workspace_name'])
                    print(f'   ✅ Workspace adı girildi: {test_data["workspace_name"]}')

                    # Submit form by pressing Enter
                    page.press('input[name="name"]', 'Enter')
                    print('   ✅ Enter tuşuna basıldı (form gönderildi)')

                    # Wait for workspace creation
                    page.wait_for_timeout(3000)

                    print('\n' + '='*80)
                    print('✅ WORKSPACE OLUŞTURULDU!')
                    print(f'📬 Gelen kutunu kontrol et: {test_data["email"]}')
                    print('📧 Workspace hazır emaili gelecek (birkaç saniye içinde)')
                    print('='*80 + '\n')
                else:
                    print('   ⚠️  Create workspace butonu bulunamadı')
                    print('   Dashboard screenshot alınıyor...')
                    page.screenshot(path=f'/tmp/dashboard_{random_id}.png')
                    print(f'   📸 Screenshot: /tmp/dashboard_{random_id}.png')

            else:
                print('   ❌ Login başarısız - dashboard\'a yönlendirilmedi')

            # Wait a bit to see the result
            page.wait_for_timeout(5000)

        except Exception as e:
            print(f'\n❌ HATA: {type(e).__name__}: {e}')

            try:
                page.screenshot(path=f'/tmp/error_{random_id}.png')
                print(f'📸 Hata screenshot: /tmp/error_{random_id}.png')
            except:
                pass

        finally:
            browser.close()

if __name__ == '__main__':
    test_workspace_creation_email()
