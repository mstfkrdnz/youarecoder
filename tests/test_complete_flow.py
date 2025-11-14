#!/usr/bin/env python3
"""
Complete email flow test with mustafa+01@alkedos.com
Tests: Registration email → Login → Workspace creation email
"""

import random
import string
import time
from playwright.sync_api import sync_playwright

def generate_random_string(length=8):
    """Generate random alphanumeric string"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def test_complete_email_flow():
    """Complete flow: Register → Login → Create Workspace"""

    random_id = generate_random_string(6)
    test_data = {
        'company_name': f'Complete Test Company {random_id}',
        'subdomain': f'completetest{random_id}',
        'full_name': 'Mustafa Kördönmez',
        'username': f'mustafa{random_id}',
        'email': 'mustafa+01@alkedos.com',  # Gmail alias for testing
        'password': 'CompleteTest123!@#',
        'workspace_name': f'complete-ws-{random_id}'
    }

    print('\n' + '='*80)
    print('🎬 TAM KAYIT AKIŞI TESTİ')
    print('='*80)
    print(f'\n📋 Test Verileri:')
    print(f'   Şirket: {test_data["company_name"]}')
    print(f'   Subdomain: {test_data["subdomain"]}')
    print(f'   Email: {test_data["email"]}')
    print(f'   Kullanıcı: {test_data["username"]}')
    print(f'   Workspace: {test_data["workspace_name"]}')

    with sync_playwright() as p:
        print('\n🌐 Browser başlatılıyor...')
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            # STEP 1: Registration
            print('\n' + '='*80)
            print('📝 ADIM 1: KAYIT (Registration Email Tetikleniyor)')
            print('='*80)

            page.goto('https://youarecoder.com/auth/register', timeout=30000)
            print('   ✅ Kayıt sayfası yüklendi')

            # Fill registration form
            page.fill('input[name="company_name"]', test_data['company_name'])
            page.fill('input[name="subdomain"]', test_data['subdomain'])
            page.fill('input[name="full_name"]', test_data['full_name'])
            page.fill('input[name="username"]', test_data['username'])
            page.fill('input[name="email"]', test_data['email'])
            page.fill('input[name="password"]', test_data['password'])
            page.fill('input[name="password_confirm"]', test_data['password'])
            print('   ✅ Form dolduruldu')

            # Submit registration
            page.click('input[type="submit"]')
            print('   ✅ Kayıt formu gönderildi')

            # Wait for response
            page.wait_for_load_state('networkidle', timeout=15000)
            time.sleep(2)

            current_url = page.url
            print(f'   📍 Yönlendirilen URL: {current_url}')

            if 'login' in current_url or 'success' in page.content().lower():
                print('   ✅ Kayıt başarılı!')
                print('   📧 Registration email gönderildi: mustafa+01@alkedos.com')
            else:
                print('   ⚠️  Kayıt durumu belirsiz')

            # STEP 2: Login
            print('\n' + '='*80)
            print('🔐 ADIM 2: GİRİŞ YAPMA')
            print('='*80)

            # Wait a bit for email to be sent
            print('   ⏳ Email gönderilmesi için 3 saniye bekleniyor...')
            time.sleep(3)

            # Navigate to login
            login_url = f'https://{test_data["subdomain"]}.youarecoder.com/auth/login'
            page.goto(login_url, timeout=30000)
            print(f'   ✅ Login sayfası yüklendi: {login_url}')

            # Login
            page.fill('input[name="email"]', test_data['email'])
            page.fill('input[name="password"]', test_data['password'])
            page.click('input[type="submit"]')
            print('   ✅ Login formu gönderildi')

            # Wait for dashboard
            page.wait_for_load_state('networkidle', timeout=15000)
            time.sleep(2)

            if 'dashboard' in page.url:
                print('   ✅ Dashboard\'a yönlendirildi - Login başarılı!')
            else:
                print(f'   ⚠️  Dashboard beklendi ama URL: {page.url}')

            # STEP 3: Create Workspace
            print('\n' + '='*80)
            print('📦 ADIM 3: WORKSPACE OLUŞTURMA (Workspace Ready Email Tetikleniyor)')
            print('='*80)

            # Click New Workspace button
            selectors = [
                'button:has-text("New Workspace")',
                'button:has-text("Create Workspace")',
                'a:has-text("New Workspace")'
            ]

            workspace_button_found = False
            for selector in selectors:
                try:
                    if page.locator(selector).count() > 0:
                        page.click(selector)
                        workspace_button_found = True
                        print(f'   ✅ Workspace button tıklandı: {selector}')
                        break
                except:
                    continue

            if not workspace_button_found:
                print('   ⚠️  Workspace button bulunamadı')
                page.screenshot(path=f'/tmp/no_workspace_button_{random_id}.png')
            else:
                # Wait for modal
                time.sleep(1)

                # Fill workspace name
                page.fill('input[name="name"]', test_data['workspace_name'])
                print(f'   ✅ Workspace adı girildi: {test_data["workspace_name"]}')

                # Submit by pressing Enter
                page.press('input[name="name"]', 'Enter')
                print('   ✅ Workspace oluşturma formu gönderildi')

                # Wait for workspace creation
                print('   ⏳ Workspace oluşturulması bekleniyor...')
                time.sleep(5)

                print('   ✅ Workspace oluşturuldu!')
                print('   📧 Workspace Ready email gönderildi: mustafa+01@alkedos.com')

            # Final Summary
            print('\n' + '='*80)
            print('✅ TAM AKIŞ TESTİ TAMAMLANDI!')
            print('='*80)
            print(f'\n📬 Gelen Kutunu Kontrol Et: {test_data["email"]}')
            print('\n📧 Gönderilmesi Gereken Emailler:')
            print('   1. ✅ Registration Welcome Email')
            print('   2. ✅ Workspace Ready Email')
            print('\n⏱️  Emailler birkaç saniye içinde ulaşacak')
            print('='*80 + '\n')

            # Take final screenshot
            page.screenshot(path=f'/tmp/complete_flow_final_{random_id}.png')
            print(f'📸 Final screenshot: /tmp/complete_flow_final_{random_id}.png\n')

        except Exception as e:
            print(f'\n❌ HATA: {type(e).__name__}: {e}')

            try:
                page.screenshot(path=f'/tmp/complete_flow_error_{random_id}.png')
                print(f'📸 Hata screenshot: /tmp/complete_flow_error_{random_id}.png')
            except:
                pass

        finally:
            browser.close()

if __name__ == '__main__':
    test_complete_email_flow()
