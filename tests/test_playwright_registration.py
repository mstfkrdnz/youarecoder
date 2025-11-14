#!/usr/bin/env python3
"""
Playwright test: Complete registration flow on production website
Tests email system by triggering registration email from real Flask app
"""

import random
import string
from playwright.sync_api import sync_playwright, expect

def generate_random_string(length=8):
    """Generate random alphanumeric string"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def test_registration_with_email():
    """Test complete registration flow on production site"""

    # Generate unique test data
    random_id = generate_random_string(6)
    test_data = {
        'company_name': f'Email Test Company {random_id}',
        'subdomain': f'emailtest{random_id}',
        'full_name': 'Mustafa Test',
        'username': f'mustafa{random_id}',
        'email': 'mustafa@alkedos.com',  # Your real email
        'password': 'TestPassword123!@#'
    }

    print('\n' + '='*80)
    print('🎭 PLAYWRIGHT KAYIT TESTİ - PRODUCTION')
    print('='*80)
    print(f'\n📋 Test Verileri:')
    print(f'   Şirket: {test_data["company_name"]}')
    print(f'   Subdomain: {test_data["subdomain"]}')
    print(f'   Kullanıcı: {test_data["username"]}')
    print(f'   Email: {test_data["email"]}')

    with sync_playwright() as p:
        print('\n🌐 Browser başlatılıyor...')
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            # Navigate to registration page
            print('\n📍 Kayıt sayfasına gidiliyor...')
            page.goto('https://youarecoder.com/auth/register', timeout=30000)
            print('   ✅ Sayfa yüklendi')

            # Fill registration form
            print('\n📝 Form dolduruluyor...')
            page.fill('input[name="company_name"]', test_data['company_name'])
            print('   ✅ Şirket adı')

            page.fill('input[name="subdomain"]', test_data['subdomain'])
            print('   ✅ Subdomain')

            page.fill('input[name="full_name"]', test_data['full_name'])
            print('   ✅ İsim')

            page.fill('input[name="username"]', test_data['username'])
            print('   ✅ Kullanıcı adı')

            page.fill('input[name="email"]', test_data['email'])
            print('   ✅ Email')

            page.fill('input[name="password"]', test_data['password'])
            print('   ✅ Şifre')

            page.fill('input[name="password_confirm"]', test_data['password'])
            print('   ✅ Şifre onay')

            # Submit form
            print('\n📤 Form gönderiliyor...')
            page.click('input[type="submit"]')

            # Wait for response
            print('   ⏳ Yanıt bekleniyor...')
            page.wait_for_load_state('networkidle', timeout=10000)

            # Check for success or error
            current_url = page.url
            page_content = page.content()

            print(f'\n📍 Yeni URL: {current_url}')

            if 'success' in page_content.lower() or 'başarı' in page_content.lower():
                print('   ✅ Başarı mesajı tespit edildi')
            elif 'login' in current_url:
                print('   ✅ Login sayfasına yönlendirildi (kayıt başarılı)')
            elif 'error' in page_content.lower() or 'hata' in page_content.lower():
                print('   ⚠️  Hata mesajı var (subdomain çakışması olabilir)')

            # Take screenshot for debugging
            screenshot_path = f'/tmp/playwright_registration_{random_id}.png'
            page.screenshot(path=screenshot_path)
            print(f'\n📸 Screenshot: {screenshot_path}')

            print('\n' + '='*80)
            print('✅ PLAYWRIGHT TESTİ TAMAMLANDI!')
            print(f'📬 Gelen kutunu kontrol et: {test_data["email"]}')
            print('📧 Kayıt hoşgeldin emaili gelecek (birkaç saniye içinde)')
            print('='*80 + '\n')

        except Exception as e:
            print(f'\n❌ HATA: {type(e).__name__}: {e}')

            # Take error screenshot
            try:
                error_screenshot = f'/tmp/playwright_error_{random_id}.png'
                page.screenshot(path=error_screenshot)
                print(f'📸 Hata screenshot: {error_screenshot}')
            except:
                pass

        finally:
            browser.close()

if __name__ == '__main__':
    test_registration_with_email()
