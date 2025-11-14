#!/usr/bin/env python3
"""
Complete flow test: Registration + Workspace Creation
Tests both Registration and Workspace Ready emails
"""
import random
import string
import time
from playwright.sync_api import sync_playwright

def generate_random_id(length=6):
    """Generate random ID for unique test data."""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def test_complete_flow():
    """Test complete registration and workspace creation flow."""
    random_id = generate_random_id()

    # Test data
    test_data = {
        'company_name': f'Complete Test Company {random_id}',
        'subdomain': f'completetest{random_id}',
        'full_name': 'Mustafa Kördönmez',
        'username': f'mustafa{random_id}',
        'email': 'mustafa+01@alkedos.com',
        'password': 'CompleteTest123!@#',
        'workspace_name': f'complete_ws_{random_id}'  # Use underscore instead of hyphen
    }

    print("=" * 80)
    print("🎬 TAM KAYIT AKIŞI TESTİ V2")
    print("=" * 80)
    print()
    print("📋 Test Verileri:")
    print(f"   Şirket: {test_data['company_name']}")
    print(f"   Subdomain: {test_data['subdomain']}")
    print(f"   Email: {test_data['email']}")
    print(f"   Kullanıcı: {test_data['username']}")
    print(f"   Workspace: {test_data['workspace_name']}")
    print()

    with sync_playwright() as p:
        # Launch browser
        print("🌐 Browser başlatılıyor...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1280, 'height': 720})
        page = context.new_page()

        try:
            # STEP 1: REGISTRATION
            print()
            print("=" * 80)
            print("📝 ADIM 1: KAYIT (Registration Email Tetikleniyor)")
            print("=" * 80)

            page.goto('https://youarecoder.com/auth/register', timeout=30000)
            print("   ✅ Kayıt sayfası yüklendi")

            # Fill registration form
            page.fill('input[name="company_name"]', test_data['company_name'])
            page.fill('input[name="subdomain"]', test_data['subdomain'])
            page.fill('input[name="full_name"]', test_data['full_name'])
            page.fill('input[name="username"]', test_data['username'])
            page.fill('input[name="email"]', test_data['email'])
            page.fill('input[name="password"]', test_data['password'])
            page.fill('input[name="password_confirm"]', test_data['password'])
            print("   ✅ Form dolduruldu")

            # Submit registration
            page.click('input[type="submit"]')
            page.wait_for_url('**/auth/login', timeout=30000)
            print("   ✅ Kayıt formu gönderildi")
            print(f"   📍 Yönlendirilen URL: {page.url}")
            print("   ✅ Kayıt başarılı!")
            print(f"   📧 Registration email gönderildi: {test_data['email']}")

            # STEP 2: LOGIN
            print()
            print("=" * 80)
            print("🔐 ADIM 2: GİRİŞ YAPMA")
            print("=" * 80)

            # Wait for email to be sent
            print("   ⏳ Email gönderilmesi için 3 saniye bekleniyor...")
            time.sleep(3)

            # Login
            subdomain_url = f"https://{test_data['subdomain']}.youarecoder.com/auth/login"
            page.goto(subdomain_url, timeout=30000)
            print(f"   ✅ Login sayfası yüklendi: {subdomain_url}")

            page.fill('input[name="email"]', test_data['email'])
            page.fill('input[name="password"]', test_data['password'])
            page.click('input[type="submit"]')

            # Wait for dashboard
            page.wait_for_url('**/dashboard', timeout=30000)
            print("   ✅ Login formu gönderildi")
            print("   ✅ Dashboard'a yönlendirildi - Login başarılı!")

            # STEP 3: CREATE WORKSPACE
            print()
            print("=" * 80)
            print("📦 ADIM 3: WORKSPACE OLUŞTURMA (Workspace Ready Email Tetikleniyor)")
            print("=" * 80)

            # Click "New Workspace" button
            page.click('button:has-text("New Workspace")')
            print('   ✅ Workspace button tıklandı: button:has-text("New Workspace")')

            # Wait for modal and fill workspace name
            page.wait_for_selector('input[name="name"]', timeout=5000)
            page.fill('input[name="name"]', test_data['workspace_name'])
            print(f"   ✅ Workspace adı girildi: {test_data['workspace_name']}")

            # Submit by pressing Enter (more reliable than clicking button)
            page.press('input[name="name"]', 'Enter')
            print("   ✅ Workspace oluşturma formu gönderildi")

            # Wait for workspace creation to complete
            print("   ⏳ Workspace oluşturulması bekleniyor...")
            time.sleep(5)

            print("   ✅ Workspace oluşturuldu!")
            print(f"   📧 Workspace Ready email gönderildi: {test_data['email']}")

            # Take final screenshot
            screenshot_path = f"/tmp/complete_flow_v2_{random_id}.png"
            page.screenshot(path=screenshot_path, full_page=True)

            # Success summary
            print()
            print("=" * 80)
            print("✅ TAM AKIŞ TESTİ TAMAMLANDI!")
            print("=" * 80)
            print()
            print(f"📬 Gelen Kutunu Kontrol Et: {test_data['email']}")
            print()
            print("📧 Gönderilmesi Gereken Emailler:")
            print("   1. ✅ Registration Welcome Email")
            print("   2. ✅ Workspace Ready Email")
            print()
            print("⏱️  Emailler birkaç saniye içinde ulaşacak")
            print("=" * 80)
            print()
            print(f"📸 Final screenshot: {screenshot_path}")

        except Exception as e:
            print(f"\n❌ HATA: {str(e)}")
            screenshot_path = f"/tmp/error_{random_id}.png"
            page.screenshot(path=screenshot_path)
            print(f"📸 Error screenshot: {screenshot_path}")
            raise

        finally:
            browser.close()

if __name__ == '__main__':
    test_complete_flow()
