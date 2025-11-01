# YouAreCoder Platform - Comprehensive Master Plan

**Vision**: Complete Software Development Lifecycle (SDLC) Platform
**Version**: 2.1
**Date**: 2025-11-01
**Status**: Evolution from Code-Server Hosting → Full SDLC Platform

---

## Executive Summary

YouAreCoder platform yolculuğunun başlangıcında basit bir code-server hosting hizmeti olarak tasarlandı. Şimdi ise yazılım geliştirme yaşam döngüsünün tüm aşamalarını kapsayan, rol tabanlı işbirliği özellikleriyle donatılmış, kurumsal seviyede bir platforma evrilmesinin yol haritasını çiziyoruz.

### Mevcut Durum
- **Çalışan sistem**: Multi-tenant SaaS, PayTR entegrasyonu, email bildirimleri
- **Roller**: Owner (yönetici) + Developer (geliştirici)
- **Workspace yönetimi**: Manuel oluşturma, temel izolasyon
- **Canlı ödeme sistemi**: ✅ Başarıyla test edildi (₺2,970 Team planı)

### Hedef Durum
- **Tam SDLC platformu**: Analist, Developer, Tester, Client, AI Agent rolleri
- **Template sistemi**: Hızlı workspace hazırlama (Python, Node.js, React, vb.)
- **Kişisel kotalar**: Her developer için workspace limitleri
- **Lifecycle yönetimi**: Start/stop/restart/logs/monitoring
- **İşbirliği özellikleri**: Workspace paylaşımı, gerçek zamanlı iletişim

### İmplementasyon Zaman Çizelgesi
5 aşama, 6-9 aylık süreç:
1. **Dashboard Düzeltmeleri** (1 gün) - UI tutarlılığı
2. **Kota & Ekip Yönetimi** (1-2 hafta) - Temel altyapı
3. **Template Sistemi** (2-3 hafta) - Hızlı provisioning
4. **Lifecycle Yönetimi** (2-3 hafta) - Operasyonel olgunluk
5. **Gelecek Vizyonu** (3+ ay) - Tam SDLC özellikleri

---

## İçindekiler

1. [Mevcut Durum Değerlendirmesi](#1-mevcut-durum-değerlendirmesi)
2. [Vizyon & Mimari](#2-vizyon--mimari)
3. [Veritabanı Şema Evrimi](#3-veritabanı-şema-evrimi)
4. [İmplementasyon Aşamaları](#4-implementasyon-aşamaları)
5. [Teknik Spesifikasyonlar](#5-teknik-spesifikasyonlar)
6. [İş Modeli Uyumu](#6-iş-modeli-uyumu)
7. [Güvenlik & Uyumluluk](#7-güvenlik--uyumluluk)
8. [Test Stratejisi](#8-test-stratejisi)
9. [Deployment & Operasyonlar](#9-deployment--operasyonlar)
10. [Başarı Metrikleri](#10-başarı-metrikleri)
11. [Risk Yönetimi](#11-risk-yönetimi)
12. [Ekler](#12-ekler)

---

## 1. Mevcut Durum Değerlendirmesi

### 1.1 Mimari Genel Bakış

**Teknoloji Stack:**
- Backend: Flask + SQLAlchemy + PostgreSQL
- Frontend: Jinja2 templates + Alpine.js + Tailwind CSS
- Infrastructure: Linux users + systemd + code-server + Traefik
- Authentication: Flask-Login with bcrypt password hashing
- Rate Limiting: Flask-Limiter (environment-specific configuration)

**Deployment Mimarisi:**
- Production Server: 37.27.21.167
- Reverse Proxy: Traefik with automatic SSL (Let's Encrypt)
- Database: PostgreSQL 15
- Service Management: systemd for Flask app + code-server instances

### 1.2 Mevcut Veritabanı Şeması

**Companies Tablosu:**
```python
class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    subdomain = db.Column(db.String(50), unique=True, nullable=False)
    admin_email = db.Column(db.String(120), nullable=False)
    plan = db.Column(db.String(20), default='free')  # free, starter, team, enterprise
    max_workspaces = db.Column(db.Integer, default=3)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

**Users Tablosu:**
```python
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), default='member')  # admin, member
    # ← Eklenecek: workspace_quota (Faz 2)
    is_active = db.Column(db.Boolean, default=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

**Workspaces Tablosu:**
```python
class Workspace(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    subdomain = db.Column(db.String(50), unique=True, nullable=False)
    linux_username = db.Column(db.String(50), unique=True, nullable=False)
    port = db.Column(db.Integer, unique=True, nullable=False)
    code_server_password = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, active, error
    disk_quota_gb = db.Column(db.Integer, default=10)
    # ← Eklenecek: template_id, is_running, lifecycle fields (Faz 3-4)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'))
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
```

### 1.3 Mevcut Özellikler

**✅ İmplemente Edilmiş:**
- Multi-tenant company registration
- User authentication with password validation
- Owner role with company management
- Basic workspace provisioning (Linux user + code-server)
- Subdomain-based access (workspace.youarecoder.com)
- SSL certificates via Let's Encrypt
- Workspace listing and basic info display
- Plan-based workspace limits (company-wide)
- PayTR payment integration (live, tested)
- Email notifications (Mailjet SMTP)
- Multi-currency support (USD, EUR, TRY)
- Dynamic currency pricing with TCMB exchange rates
- Automated exchange rate updates (3x daily cronjob)
- Multi-language support (EN, TR)
- Rate limiting (configurable per environment)
- Form data persistence on validation errors
- Payment history filtering (hide pending payments)

**❌ Eksik (Vizyon için Gerekli):**
- Per-developer workspace quotas (Faz 2)
- Workspace templates (Faz 3)
- Workspace lifecycle controls (start/stop/restart) (Faz 4)
- Real-time workspace monitoring (Faz 4)
- Resource usage tracking (Faz 4)
- Team management UI (Faz 2)
- Advanced role system (Analyst, Tester, Client, AI Agent) (Faz 5)
- Collaboration features (Faz 5)
- AI Agent integration (Faz 5)
- Workflow automation (Faz 5)

### 1.4 Dinamik Kur Sistemi (Yeni Eklenen)

**Amaç:** USD/EUR fiyatları güncel TCMB kurlarına göre TRY'ye otomatik dönüştür

**Mimari:**
- **Base Currency:** USD (Single Source of Truth)
- **Exchange Rate Source:** TCMB (Türkiye Cumhuriyet Merkez Bankası) XML API
- **Update Frequency:** Günde 3 kez (16:00, 17:00, 18:00 UTC)
- **Fallback:** TCMB erişilemezse statik kurlar kullanılır

**Teknik Detaylar:**
```python
# Base USD Prices
BASE_PRICES_USD = {
    'starter': 29,
    'team': 99,
    'enterprise': 299
}

# Dynamic conversion via ExchangeRate model
try_price = ExchangeRate.calculate_try_price(usd_price)
eur_price = ExchangeRate.calculate_eur_price(usd_price)
```

**Database Schema:**
```sql
CREATE TABLE exchange_rates (
    id SERIAL PRIMARY KEY,
    source_currency VARCHAR(3) NOT NULL,    -- USD, EUR
    target_currency VARCHAR(3) NOT NULL,    -- TRY
    rate NUMERIC(10, 4) NOT NULL,
    effective_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(source_currency, target_currency, effective_date)
);
```

**Cronjob Configuration:**
```bash
# /root/youarecoder/scripts/update-exchange-rates.sh
0 16 * * * /root/youarecoder/scripts/update-exchange-rates.sh
0 17 * * * /root/youarecoder/scripts/update-exchange-rates.sh
0 18 * * * /root/youarecoder/scripts/update-exchange-rates.sh
```

**CLI Command:**
```bash
# Manuel kur güncelleme
flask update-exchange-rates

# Belirli bir tarih için
flask update-exchange-rates --date 2025-10-31
```

**Billing UI Features:**
- Currency selector (TRY, USD, EUR) with flag icons
- Real-time price conversion without page reload
- Exchange rate date display (örn: "💱 Exchange rates from 2025-10-31")
- localStorage ile seçilen para birimi hatırlanır
- Default currency: USD

**Error Handling:**
- TCMB API erişilemezse fallback kurlar kullanılır
- Hafta sonu için son iş günü kurları geçerlidir
- Başarısız güncelleme denemeleri loglanır
- Retry mekanizması ile 3 günlük deneme

**Monitoring:**
- Log dosyası: `/var/log/youarecoder/exchange-rates.log`
- Database query: `SELECT * FROM exchange_rates ORDER BY effective_date DESC`
- Cronjob status: `crontab -l | grep exchange-rates`

### 1.5 Mevcut Kullanıcı İş Akışları

**Owner İş Akışı:**
1. Company kaydı (owner hesabı otomatik oluşur)
2. Ekip üyelerine email ile davetiye gönder
3. Company dashboard'unda tüm workspaces ve ekip üyelerini görüntüle
4. Workspace kullanımını plan limitlerine karşı izle
5. Plan upgrade/downgrade yap

**Developer İş Akışı:**
1. Davetiye al, hesap oluştur
2. Workspace oluştur (isim, template seç)
3. Subdomain URL üzerinden workspace'e eriş
4. code-server ile geliştirme yap
5. Dashboard'da kişisel workspace'leri görüntüle

### 1.5 Mevcut Sorun Noktaları

1. **Workspace Kotası Yok:** Company limiti tüm kullanıcılar tarafından paylaşılıyor, bireysel kontrol yok
2. **Manuel Kurulum:** Her workspace manual konfigürasyon gerektiriyor
3. **Lifecycle Kontrolü Yok:** Workspace'ler durdurulamıyor, sürekli çalışıyor
4. **Template Yok:** Her workspace boş başlıyor
5. **Sınırlı Dashboard:** Karışık metrikler gösteriliyor (kişisel + company)
6. **Kaynak İzleme Yok:** CPU/memory/disk kullanımı görünmüyor
7. **Temel Rol Sistemi:** Sadece admin/member, özelleşmiş roller yok
8. **İşbirliği Yok:** Workspace veya dosya paylaşımı yapılamıyor

---

## 2. Vizyon & Mimari

### 2.1 Platform Evrim Aşamaları

**Faz 0: Code-Server Hosting (Mevcut)**
- Temel workspace provisioning
- Owner + Developer rolleri
- Manuel yönetim

**Faz 1: Developer Platform (Hedef)**
- Developer başına kotalar
- Template sistemi
- Lifecycle yönetimi
- Kaynak izleme

**Faz 2: Ekip İşbirliği**
- Workspace paylaşımı
- Rol tabanlı erişim (Analyst, Tester)
- Gerçek zamanlı işbirliği
- Aktivite feed'leri

**Faz 3: Tam SDLC Platformu**
- Client portalı
- AI Agent entegrasyonu
- Workflow otomasyonu
- Gelişmiş analytics

### 2.2 Rol Sistemi Mimarisi

**Owner Rolü:**
- Company yöneticisi
- Ekip üyelerini yönet (davet, çıkar, kota ata)
- Tüm company workspace'lerini görüntüle
- Billing ve plan yönetimi
- Analytics ve raporlara erişim
- Company ayarlarını yapılandır

**Developer Rolü:**
- Workspace oluştur (kişisel kota dahilinde)
- Sahip olunan workspace'ler üzerinde tam kontrol (start/stop/delete)
- Paylaşılan workspace'lere erişim (read veya write)
- Kişisel dashboard görüntüle
- Extension kurma ve environment konfigürasyonu

**Analyst Rolü (Gelecek):**
- Workspace'e read-only erişim
- Kod ve dökümantasyon görüntüleme
- Requirement ve spesifikasyon oluşturma
- Kod ve issue'lar üzerine yorum yapma
- Rapor oluşturma

**Tester Rolü (Gelecek):**
- Test amaçlı workspace erişimi
- Test çalıştırma ve sonuçları görüntüleme
- Bug ve issue raporlama
- Staging/testing environment'lara erişim
- Performance monitoring

**Client Rolü (Gelecek):**
- Proje ilerlemesini görüntüleme
- Demo environment'lara erişim
- Feedback sağlama
- Deliverable'ları onaylama
- Sınırlı workspace erişimi (proje bazında yapılandırılabilir)

**AI Agent Rolü (Gelecek):**
- Otomatik kod üretimi
- Test otomasyonu
- Kod review ve öneriler
- Dökümantasyon üretimi
- Deployment otomasyonu

### 2.3 Workspace Mimarisi

**Workspace = İzole Code-Server Instance**
- Ayrı Linux kullanıcı hesabı
- Ayrılmış home directory
- İzole filesystem
- code-server için unique port
- systemd ile process izolasyonu
- Resource limitleri (CPU, memory, disk)

**Neden Birden Fazla Workspace?**
- Farklı runtime environment'lar (Python 3.11 vs Node 18)
- Güvenlik izolasyonu (hassas client dataları)
- Kaynak izolasyonu (ağır ML training vs web dev)
- Stabilite izolasyonu (deneysel vs production kodu)
- Tipik kullanım: Developer başına 1-2 workspace

**VS Code Multi-Root Workspace'ler:**
- Bir code-server instance'ı birden fazla proje klasörü açabilir
- Sadece farklı projeler için ayrı instance'lara gerek yok
- Ayrı instance'lar sadece izolasyon ihtiyacı için kullanılmalı

### 2.4 Template Sistemi

**Amaç:** Önceden yapılandırılmış environment'larla hızlı workspace provisioning

**Template Bileşenleri:**
1. **Base Image:** OS + runtime + araçlar
2. **Git Repositories:** Belirtilen repo'ları otomatik clone et
3. **VS Code Extensions:** Extension listesini otomatik kur
4. **Settings:** User settings, keybindings, snippets
5. **Run Configurations:** Debug için launch config'leri
6. **Environment Variables:** Önceden ayarlanmış ENV değişkenleri
7. **Scripts:** Post-creation setup scriptleri

**Template Tipleri:**
- **Official Templates:** YouAreCoder tarafından bakımı yapılan (Python, Node.js, React, vb.)
- **Company Templates:** Company bazında özel template'ler
- **User Templates:** Kullanıcılar tarafından oluşturulan kişisel template'ler
- **Shared Templates:** Community katkılı template'ler

**Örnek Template (Python Data Science):**
```json
{
  "name": "Python Data Science",
  "description": "Python 3.11 with Jupyter, pandas, numpy, matplotlib",
  "category": "data-science",
  "base_image": "python:3.11",
  "packages": ["jupyter", "pandas", "numpy", "matplotlib", "scikit-learn"],
  "extensions": [
    "ms-python.python",
    "ms-toolsai.jupyter",
    "ms-python.vscode-pylance"
  ],
  "repositories": [],
  "settings": {
    "python.defaultInterpreterPath": "/usr/bin/python3.11",
    "jupyter.notebookFileRoot": "${workspaceFolder}"
  },
  "post_create_script": "pip install -r requirements.txt"
}
```

### 2.5 Kota Sistemi

**Company Kotası:**
- Plan başına izin verilen toplam workspace (örn: Business plan için 10)
- Subscription plan'e göre yönetiliyor

**Developer Kotası:**
- Belirli developer'a atanan workspace limiti
- Owner tarafından belirleniyor (örn: Senior Dev: 3, Junior Dev: 1)
- Default: Company kotasının eşit dağılımı
- Company kotasını aşabilir (oversubscription modeli)

**Kota Enforcement:**
- Workspace creation anında kontrol
- UI'da kullanımı göster (X / Y workspaces)
- Geçici kota artışına izin ver (grace period)
- Kota aşıldığında owner'ı bilgilendir

**Örnek Senaryo:**
- Company Plan: Team (10 workspace)
- Ekip: 5 developer
- Default allocation: Her birine 2 workspace
- Custom allocation: Senior Dev (3), Junior'lar (1'er), Toplam: 7
- Gelecek atama için mevcut: 3 workspace

### 2.6 Workspace Lifecycle

**Durumlar:**
- **Creating:** İlk provisioning (Linux user, code-server setup)
- **Stopped:** Workspace var ama code-server çalışmıyor
- **Starting:** code-server servisi başlatılıyor
- **Running:** Aktif ve erişilebilir
- **Stopping:** code-server servisi kapatılıyor
- **Error:** Müdahale gerektiren başarısız durum
- **Deleting:** Temizlik süreci devam ediyor

**Operasyonlar:**
- **Create:** Yeni workspace provision et (template uygula, environment kur)
- **Start:** code-server servisini başlat (systemctl start)
- **Stop:** code-server servisini durdur (systemctl stop)
- **Restart:** Stop + Start
- **Delete:** Servisi durdur, Linux user'ı temizle, data'yı sil
- **View Logs:** code-server loglarına eriş
- **Monitor:** Gerçek zamanlı kaynak kullanımı (CPU, memory, disk)

**Lifecycle Kuralları:**
- Yeni workspace'ler "Creating" durumunda başlar
- Oluşturulduktan sonra kullanıcı tercihe göre auto-start
- Durdurulan workspace'ler compute kaynağı tüketmez
- Durdurulan workspace'ler hala kotadan sayılır
- Silinen workspace'ler kotayı hemen serbest bırakır

---

## 3. Veritabanı Şema Evrimi

### 3.1 Faz 2: Kota & Ekip Yönetimi

**Users tablosuna eklemeler:**
```python
class User(UserMixin, db.Model):
    # ... mevcut fieldlar ...
    workspace_quota = db.Column(db.Integer, nullable=False, default=1)
    quota_assigned_at = db.Column(db.DateTime)
    quota_assigned_by = db.Column(db.Integer, db.ForeignKey('users.id'))
```

**Migration Script:**
```python
"""Add workspace quota to users

Revision ID: add_user_workspace_quota
Revises: previous_migration
Create Date: 2025-11-01
"""

def upgrade():
    op.add_column('users', sa.Column('workspace_quota', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('users', sa.Column('quota_assigned_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('quota_assigned_by', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_quota_assigned_by', 'users', 'users', ['quota_assigned_by'], ['id'])

    # Initialize quotas: equal distribution of company max_workspaces
    connection = op.get_bind()
    companies = connection.execute("SELECT id, max_workspaces FROM companies")
    for company_id, max_workspaces in companies:
        user_count = connection.execute(
            "SELECT COUNT(*) FROM users WHERE company_id = %s AND role != 'admin'",
            (company_id,)
        ).scalar()
        if user_count > 0:
            quota_per_user = max(1, max_workspaces // user_count)
            connection.execute(
                "UPDATE users SET workspace_quota = %s WHERE company_id = %s AND role != 'admin'",
                (quota_per_user, company_id)
            )

def downgrade():
    op.drop_constraint('fk_quota_assigned_by', 'users', type_='foreignkey')
    op.drop_column('users', 'quota_assigned_by')
    op.drop_column('users', 'quota_assigned_at')
    op.drop_column('users', 'workspace_quota')
```

### 3.2 Faz 3: Template Sistemi

**Yeni WorkspaceTemplate tablosu:**
```python
class WorkspaceTemplate(db.Model):
    __tablename__ = 'workspace_templates'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))  # web, data-science, mobile, etc.
    visibility = db.Column(db.String(20), default='company')  # official, company, user
    is_active = db.Column(db.Boolean, default=True)

    # Template configuration (JSON)
    config = db.Column(db.JSON, nullable=False)

    # Ownership
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Metadata
    usage_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    workspaces = db.relationship('Workspace', backref='template', lazy='dynamic')
```

**Workspaces tablosuna eklemeler:**
```python
class Workspace(db.Model):
    # ... mevcut fieldlar ...
    template_id = db.Column(db.Integer, db.ForeignKey('workspace_templates.id'), nullable=True)
    template_applied_at = db.Column(db.DateTime)
```

### 3.3 Faz 4: Lifecycle Yönetimi

**Workspaces tablosuna eklemeler:**
```python
class Workspace(db.Model):
    # ... mevcut fieldlar ...
    is_running = db.Column(db.Boolean, default=False, nullable=False)
    last_started_at = db.Column(db.DateTime)
    last_stopped_at = db.Column(db.DateTime)
    last_accessed_at = db.Column(db.DateTime)
    auto_stop_hours = db.Column(db.Integer, default=0)  # 0 = never auto-stop
    cpu_limit_percent = db.Column(db.Integer, default=100)
    memory_limit_mb = db.Column(db.Integer, default=2048)
```

**Yeni WorkspaceLogs tablosu:**
```python
class WorkspaceLog(db.Model):
    __tablename__ = 'workspace_logs'

    id = db.Column(db.Integer, primary_key=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspaces.id'), nullable=False)
    event_type = db.Column(db.String(20), nullable=False)  # start, stop, restart, error
    message = db.Column(db.Text)
    severity = db.Column(db.String(10), default='info')  # info, warning, error
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    workspace = db.relationship('Workspace', backref=db.backref('logs', lazy='dynamic'))
    user = db.relationship('User')
```

**Yeni WorkspaceMetrics tablosu:**
```python
class WorkspaceMetrics(db.Model):
    __tablename__ = 'workspace_metrics'

    id = db.Column(db.Integer, primary_key=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspaces.id'), nullable=False)

    # Resource usage
    cpu_percent = db.Column(db.Float, default=0)
    memory_mb = db.Column(db.Integer, default=0)
    disk_used_gb = db.Column(db.Float, default=0)

    # Network
    network_in_mb = db.Column(db.Float, default=0)
    network_out_mb = db.Column(db.Float, default=0)

    # Timestamp
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Relationships
    workspace = db.relationship('Workspace', backref=db.backref('metrics', lazy='dynamic'))
```

---

## 4. İmplementasyon Aşamaları

### Faz 1: Dashboard Düzeltmeleri (1 Gün)

**Hedef:** Dashboard metrik tutarsızlıklarını düzelt ve UX iyileştir

**Kapsam:**
- Yanıltıcı "Team Members" kartını kaldır
- "Workspace Quota" kartı ekle (kişisel kullanım göster)
- Workspace listesinin sadece owner'ın workspace'lerini göstermesini sağla
- Dashboard layout ve netliği iyileştir

**Teknik Değişiklikler:**

**Dosya: app/templates/dashboard.html**
```html
<!-- BU KARTI KALDIR (satırlar 98-110) -->
<!-- Team Members card -->

<!-- BUNUN YERİNE BU KARTI EKLE -->
<div class="bg-white overflow-hidden shadow rounded-lg">
    <div class="p-5">
        <div class="flex items-center">
            <div class="flex-shrink-0">
                <svg class="h-6 w-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
            </div>
            <div class="ml-5 w-0 flex-1">
                <dl>
                    <dt class="text-sm font-medium text-gray-500 truncate">Workspace Kotası</dt>
                    <dd class="flex items-baseline">
                        <div class="text-2xl font-semibold text-gray-900">
                            {{ current_user.workspaces.count() }} / {{ current_user.workspace_quota }}
                        </div>
                        <div class="ml-2 flex items-baseline text-sm font-semibold text-gray-500">
                            {% set usage_percent = (current_user.workspaces.count() / current_user.workspace_quota * 100) if current_user.workspace_quota > 0 else 0 %}
                            <span class="{% if usage_percent >= 80 %}text-red-600{% elif usage_percent >= 60 %}text-yellow-600{% else %}text-green-600{% endif %}">
                                {{ "%.0f"|format(usage_percent) }}% kullanılıyor
                            </span>
                        </div>
                    </dd>
                </dl>
            </div>
        </div>
    </div>
</div>
```

**Kabul Kriterleri:**
- ✅ "Team Members" kartı kaldırıldı
- ✅ "Workspace Quota" kartı doğru gösteriliyor (X / Y formatı)
- ✅ Kota yüzdesi renk kodlamalı (yeşil < 60%, sarı 60-80%, kırmızı > 80%)
- ✅ Dashboard sadece kullanıcının sahip olduğu workspace'leri gösteriyor
- ✅ Tüm metrikler tutarlı (kişisel, company-wide değil)

**Zaman Tahmini:** 4-6 saat
**Risk Seviyesi:** Düşük (sadece UI değişiklikleri, veritabanı değişikliği yok)

---

### Faz 2: Kota & Ekip Yönetimi (1-2 Hafta)

**Hedef:** Developer başına workspace kotaları ve ekip yönetimi UI implement et

**Kapsam:**
- User modeline `workspace_quota` field'ı ekle
- Owner'lar için ekip yönetimi interface oluştur
- Workspace creation'da kota enforcement implement et
- Kota atama functionality ekle

**Zaman Tahmini:** 1-2 hafta
**Risk Seviyesi:** Orta (database migration, access control değişiklikleri)

---

### Faz 3: Template Sistemi (2-3 Hafta)

**Hedef:** Hızlı workspace provisioning için template sistemi

**Kapsam:**
- WorkspaceTemplate model ve CRUD operasyonları
- Official template'lerin oluşturulması (Python, Node.js, React, vb.)
- Workspace creation sırasında template seçimi
- Template application servisi (TemplateApplicator)
- Template marketplace UI

**Zaman Tahmini:** 2-3 hafta
**Risk Seviyesi:** Orta-Yüksek (karmaşık provisioning logic)

---

### Faz 4: Lifecycle Yönetimi (2-3 Hafta)

**Hedef:** Workspace start/stop/restart ve monitoring

**Kapsam:**
- Workspace lifecycle state machine
- systemd service control entegrasyonu
- Log collection ve display
- Metrics collection servisi (CPU, memory, disk)
- Real-time monitoring dashboard
- Auto-stop after inactivity

**Zaman Tahmini:** 2-3 hafta
**Risk Seviyesi:** Yüksek (sistem seviyesi operasyonlar, resource monitoring)

---

### Faz 5: Gelecek Vizyonu (3+ Ay)

**Hedef:** Tam SDLC platform özellikleri

**Kapsam:**
- Analyst, Tester, Client rolleri
- AI Agent entegrasyonu
- Workspace sharing ve collaboration
- Real-time communication (WebSocket)
- Workflow automation
- Advanced analytics

**Zaman Tahmini:** 3+ ay
**Risk Seviyesi:** Yüksek (büyük mimari değişiklikler)

---

## 5. Teknik Spesifikasyonlar

### 5.1 API Endpoints (Gelecek REST API)

**Authentication:**
```
POST   /api/v1/auth/login           - Kullanıcı girişi
POST   /api/v1/auth/logout          - Kullanıcı çıkışı
POST   /api/v1/auth/register        - Company kaydı
POST   /api/v1/auth/refresh         - JWT token yenileme
```

**User Management:**
```
GET    /api/v1/users/me             - Mevcut kullanıcı profili
PUT    /api/v1/users/me             - Profil güncelleme
GET    /api/v1/users/{id}           - Kullanıcı detayları (admin)
PUT    /api/v1/users/{id}/quota     - Kullanıcı kotası güncelleme (admin)
```

**Workspace Management:**
```
GET    /api/v1/workspaces           - Kullanıcının workspace'lerini listele
POST   /api/v1/workspaces           - Workspace oluştur
GET    /api/v1/workspaces/{id}      - Workspace detayları
PUT    /api/v1/workspaces/{id}      - Workspace ayarlarını güncelle
DELETE /api/v1/workspaces/{id}      - Workspace sil
POST   /api/v1/workspaces/{id}/start    - Workspace başlat
POST   /api/v1/workspaces/{id}/stop     - Workspace durdur
POST   /api/v1/workspaces/{id}/restart  - Workspace yeniden başlat
GET    /api/v1/workspaces/{id}/logs     - Workspace logları
GET    /api/v1/workspaces/{id}/metrics  - Kaynak metrikleri
```

**Template Management:**
```
GET    /api/v1/templates            - Mevcut template'leri listele
POST   /api/v1/templates            - Custom template oluştur
GET    /api/v1/templates/{id}       - Template detayları
PUT    /api/v1/templates/{id}       - Template güncelle
DELETE /api/v1/templates/{id}       - Template sil
```

### 5.2 Database İndeksleri (Performance Optimizasyonu)

```sql
-- User lookups
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_company ON users(company_id);
CREATE INDEX idx_users_role ON users(role);

-- Workspace lookups
CREATE INDEX idx_workspaces_owner ON workspaces(owner_id);
CREATE INDEX idx_workspaces_company ON workspaces(company_id);
CREATE INDEX idx_workspaces_subdomain ON workspaces(subdomain);
CREATE INDEX idx_workspaces_status ON workspaces(status);
CREATE INDEX idx_workspaces_is_running ON workspaces(is_running);
CREATE INDEX idx_workspaces_template ON workspaces(template_id);

-- Template lookups
CREATE INDEX idx_templates_category ON workspace_templates(category);
CREATE INDEX idx_templates_visibility ON workspace_templates(visibility);
CREATE INDEX idx_templates_company ON workspace_templates(company_id);

-- Log queries
CREATE INDEX idx_logs_workspace ON workspace_logs(workspace_id);
CREATE INDEX idx_logs_created_at ON workspace_logs(created_at DESC);
CREATE INDEX idx_logs_event_type ON workspace_logs(event_type);

-- Metrics queries
CREATE INDEX idx_metrics_workspace ON workspace_metrics(workspace_id);
CREATE INDEX idx_metrics_recorded_at ON workspace_metrics(recorded_at DESC);
CREATE INDEX idx_metrics_workspace_time ON workspace_metrics(workspace_id, recorded_at DESC);
```

---

## 6. İş Modeli Uyumu

### 6.1 Özellik-Plan Matrisi

| Özellik | Free | Starter | Team | Enterprise |
|---------|------|---------|------|------------|
| Kullanıcılar | 1 | 5 | 20 | Sınırsız |
| Workspace'ler | 1 | 3 | 10 | Sınırsız |
| Workspace Başına Storage | 5 GB | 10 GB | 20 GB | Custom |
| Template'ler | Official | Official + Custom | Tümü | Tümü + Priority |
| Lifecycle Control | Manuel | Auto-stop 8h | Tam kontrol | Gelişmiş |
| Destek | Community | Email | Priority | Dedicated |
| AI Agent'lar | - | - | 1 | 5+ |
| Custom Domain'ler | - | - | Evet | Evet |
| SSO | - | - | - | Evet |

### 6.2 Fiyatlandırma Stratejisi

**Fiyat Katmanları:**
- Free: $0/ay - Solo developer'lar, öğrenme
- Starter: $29/ay - Küçük ekipler, erken aşama
- Team: $99/ay - Büyüyen ekipler, profesyonel kullanım
- Enterprise: Custom - Büyük organizasyonlar, özel ihtiyaçlar

**Ek Eklentiler:**
- Ekstra workspace'ler: $5/workspace/ay
- Ekstra storage: $2/10GB/ay
- Ek AI agent'lar: $20/agent/ay
- Priority destek: $50/ay

---

## 7. Güvenlik & Uyumluluk

### 7.1 Güvenlik Önlemleri

**Uygulama Güvenliği:**
- OWASP Top 10 mitigasyonu
- SQL injection önleme (parametreli sorgular)
- XSS koruması (template escaping)
- CSRF koruması (Flask-WTF token'ları)
- Güvenli header'lar (Content-Security-Policy, X-Frame-Options)

**Altyapı Güvenliği:**
- SSH key tabanlı authentication (parola girişi disabled)
- Firewall konfigürasyonu (UFW ile minimal açık port)
- Otomatik güvenlik güncellemeleri (unattended-upgrades)
- Intrusion detection (fail2ban)
- Düzenli vulnerability scanning

**Workspace Güvenliği:**
- Kullanıcı izolasyonu (ayrı Linux hesapları)
- Process izolasyonu (systemd servis sınırları)
- Kaynak limitleri (cgroups for CPU/memory)
- Disk kotaları (filesystem seviyesi enforcement)
- Network segmentasyonu (gelecek: workspace başına VLAN'lar)

---

## 8. Test Stratejisi

### 8.1 Test Kapsama Gereksinimleri

**Unit Tests (Hedef: 80% coverage):**
- Models: CRUD operasyonları, ilişkiler, validasyon
- Forms: Validasyon kuralları, hata yönetimi
- Utilities: Helper fonksiyonlar, business logic
- Services: WorkspaceProvisioner, TemplateApplicator

**Integration Tests (Kritik yollar):**
- Authentication flow (register, login, logout)
- Workspace lifecycle (create, start, stop, delete)
- Kota enforcement (limit'te creation engelleme)
- Template application (settings, extensions, repos)

**E2E Tests (Kullanıcı iş akışları):**
- Company kaydı → Workspace oluştur → code-server'a eriş
- Owner developer'ı davet et → Developer workspace oluşturur
- Developer kotaya ulaşır → Owner kotayı artırır → Developer workspace oluşturur
- Template uygula → Kurulumu doğrula (extensions, repos, settings)

---

## 9. Deployment & Operasyonlar

### 9.1 Deployment Süreci

**Mevcut Production:**
- Server: 37.27.21.167
- Database: PostgreSQL 15
- Reverse Proxy: Traefik with Let's Encrypt
- Process Manager: systemd for Flask + code-server instances

**Deployment Script:**
```bash
#!/bin/bash
# deploy.sh - Production deployment script

set -e

echo "🚀 Deployment başlatılıyor..."

# Son kodu çek
git pull origin main

# Virtual environment aktive et
source venv/bin/activate

# Dependency'leri güncelle
pip install -r requirements.txt

# Database migration'ları çalıştır
flask db upgrade

# Flask uygulamasını yeniden başlat
sudo systemctl restart youarecoder

# Servisin çalıştığını doğrula
sleep 3
sudo systemctl status youarecoder

echo "✅ Deployment tamamlandı!"
```

---

## 10. Başarı Metrikleri

### 10.1 Teknik Metrikler

**Performance:**
- Workspace provisioning zamanı: <2 dakika (hedef)
- Dashboard yükleme zamanı: <1 saniye
- API yanıt zamanı (p95): <200ms
- Database sorgu zamanı (p95): <50ms

**Güvenilirlik:**
- Uygulama uptime: 99.9% (hedef)
- Başarısız workspace creation'lar: <1%
- Database availability: 99.95%
- Başarılı deployment'lar: >95%

**Kalite:**
- Test coverage: >80%
- Critical bug çözüm süresi: <24 saat
- Security vulnerability yaması: <7 gün
- Code review coverage: 100%

---

## 11. Risk Yönetimi

### 11.1 Teknik Riskler

| Risk | Olasılık | Etki | Önlem |
|------|----------|------|-------|
| Database migration hatası | Orta | Yüksek | Staging'de test et, production öncesi backup |
| Workspace provisioning hataları | Orta | Orta | Retry logic, detaylı hata loglama, manuel kurtarma |
| Performance degradasyonu | Düşük | Orta | Load testing, monitoring, resource limitleri |
| Security vulnerability | Orta | Yüksek | Düzenli güncellemeler, security scan'ler, bug bounty |
| Veri kaybı | Düşük | Kritik | Otomatik backup'lar, off-site storage, restore testing |

---

## 12. Ekler

### Ek A: Database Şema Diyagramı

```
┌──────────────────┐
│    companies     │
├──────────────────┤
│ id (PK)          │
│ name             │
│ subdomain (UQ)   │
│ admin_email      │
│ plan             │
│ max_workspaces   │
│ is_active        │
│ created_at       │
└────────┬─────────┘
         │
         │ 1:N
         │
┌────────┴─────────┐
│      users       │
├──────────────────┤
│ id (PK)          │
│ email (UQ)       │
│ password_hash    │
│ full_name        │
│ role             │
│ workspace_quota  │◄────┐
│ quota_assigned_by│─────┘ (self-referencing FK)
│ is_active        │
│ company_id (FK)  │
│ created_at       │
└────────┬─────────┘
         │
         │ 1:N (owner)
         │
┌────────┴────────────────┐
│      workspaces         │
├─────────────────────────┤
│ id (PK)                 │
│ name                    │
│ subdomain (UQ)          │
│ linux_username (UQ)     │
│ port (UQ)               │
│ code_server_password    │
│ status                  │
│ disk_quota_gb           │
│ template_id (FK) ───────┼─────┐
│ is_running              │     │
│ last_started_at         │     │
│ last_stopped_at         │     │
│ auto_stop_hours         │     │
│ cpu_limit_percent       │     │
│ memory_limit_mb         │     │
│ company_id (FK)         │     │
│ owner_id (FK)           │     │
│ created_at              │     │
│ updated_at              │     │
└─────────────────────────┘     │
                                │
         ┌──────────────────────┘
         │
         │ N:1
         │
┌────────┴──────────────────┐
│  workspace_templates      │
├───────────────────────────┤
│ id (PK)                   │
│ name                      │
│ description               │
│ category                  │
│ visibility                │
│ is_active                 │
│ config (JSON)             │
│ company_id (FK, nullable) │
│ created_by (FK)           │
│ usage_count               │
│ created_at                │
│ updated_at                │
└───────────────────────────┘
```

### Ek B: Rol Yetki Matrisi

| Yetki | Owner | Developer | Analyst | Tester | Client | AI Agent |
|-------|-------|-----------|---------|--------|--------|----------|
| Company dashboard görüntüle | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Ekip üyelerini yönet | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Workspace kotaları ata | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Billing görüntüle | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Workspace oluştur | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ |
| Kendi workspace'lerini sil | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ |
| Kendi workspace'lerini start/stop | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ |
| Template oluştur | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Kendi workspace'lerine eriş | ✅ | ✅ | 🟡 R/O | 🟡 Test | 🟡 Demo | ✅ |
| Paylaşılan workspace'lere eriş | ✅ | 🟡 Davetli | 🟡 Davetli | 🟡 Davetli | 🟡 Davetli | 🟡 Config |
| Workspace loglarını görüntüle | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ |
| Workspace metriklerini görüntüle | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ |
| Test çalıştır | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ |
| Rapor oluştur | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

**Açıklama:**
- ✅ Tam erişim
- ❌ Erişim yok
- 🟡 Sınırlı/koşullu erişim
- R/O = Read-only

### Ek C: Template Konfigürasyon Örnekleri

**Python Web Development:**
```json
{
  "name": "Python Web Development",
  "description": "Flask + SQLAlchemy + PostgreSQL development environment",
  "category": "web",
  "visibility": "official",
  "base_image": "python:3.11-slim",
  "system_packages": ["postgresql-client", "git", "curl"],
  "python_packages": [
    "flask==3.0.0",
    "flask-sqlalchemy==3.1.1",
    "flask-login==0.6.3",
    "flask-wtf==1.2.1",
    "psycopg2-binary==2.9.9",
    "python-dotenv==1.0.0",
    "pytest==7.4.3",
    "pytest-flask==1.3.0"
  ],
  "vscode_extensions": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "ms-python.debugpy",
    "wholroyd.jinja",
    "mtxr.sqltools",
    "mtxr.sqltools-driver-pg"
  ],
  "repositories": [],
  "vscode_settings": {
    "python.defaultInterpreterPath": "/usr/local/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.provider": "black",
    "editor.formatOnSave": true,
    "files.exclude": {
      "**/__pycache__": true,
      "**/*.pyc": true
    }
  },
  "environment_variables": {
    "FLASK_ENV": "development",
    "FLASK_DEBUG": "1"
  },
  "post_create_script": "#!/bin/bash\necho 'Creating virtual environment...'\npython -m venv venv\nsource venv/bin/activate\npip install --upgrade pip\nif [ -f requirements.txt ]; then\n  pip install -r requirements.txt\nfi\necho 'Setup complete!'"
}
```

---

## Sonuç

Bu Master Plan, YouAreCoder'ın basit bir code-server hosting platformundan tam özellikli bir SDLC platformuna dönüşümü için kapsamlı bir yol haritası sunuyor. Aşamalı yaklaşım şunları garanti ediyor:

1. **Hızlı Kazanımlar:** Faz 1 acil UX sorunlarını çözüyor (1 gün)
2. **Temel:** Faz 2 kota sistemi ve ekip yönetimi kuruyor (1-2 hafta)
3. **Farklılaşma:** Faz 3 hızlı provisioning için template sistemi ekliyor (2-3 hafta)
4. **Operasyonel Olgunluk:** Faz 4 lifecycle kontrolleri ve monitoring implement ediyor (2-3 hafta)
5. **Gelecek Vizyonu:** Faz 5 gelişmiş rollerle tam SDLC'ye genişliyor (3+ ay)

**Kritik Başarı Faktörleri:**
- Her fazın bağımsız değer sağladığı artımlı teslimat
- Evrim boyunca geriye dönük uyumluluğun korunması
- Her milestone'da kullanıcı geri bildiriminin dahil edilmesi
- Teknik borcun proaktif olarak ele alınması
- Güvenlik ve performance'ın baştan itibaren önceliklendirilmesi

**Sonraki Adımlar:**
1. Bu planı gözden geçir ve onayla
2. Faz 1 implementasyonuna başla (Dashboard Düzeltmeleri)
3. Haftalık ilerleme değerlendirmeleri kur
4. Her fazdan sonra kullanıcı geri bildirimi topla
5. Öğrenmelere dayalı olarak yol haritasını ayarla

---

*Doküman Versiyonu: 2.1*
*Son Güncelleme: 2025-11-01*
*Eklenen Özellikler: Dinamik kur sistemi (TCMB entegrasyonu), payment history filtering*
*Sonraki Değerlendirme: Faz 2 tamamlandıktan sonra*
