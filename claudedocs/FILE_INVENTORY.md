# YouAreCoder Project - File Inventory & Purpose Guide

**Last Updated:** 2025-11-14
**Project:** YouAreCoder - Workspace Provisioning System

---

## 📂 Directory Structure Overview

```
/home/mustafa/youarecoder/
├── app/                        ✅ CORE - Flask application source code
├── tests/                      ✅ CORE - Test suite
├── docs/                       ✅ CORE - Documentation
├── config/                     ✅ CORE - Configuration files
├── migrations/                 ✅ CORE - Database migrations
├── templates/                  ✅ CORE - Jinja2 templates (if not in app/)
├── scripts/                    ✅ CORE - Utility scripts
├── seeds/                      ✅ CORE - Database seed data
├── systemd/                    ✅ CORE - Systemd service files
├── traefik/                    ✅ CORE - Traefik reverse proxy config
├── venv/                       ⚙️ ENV - Python virtual environment
├── .git/                       🔧 VCS - Git repository
└── [Root files]                📄 Various (categorized below)
```

---

## 📋 ROOT DIRECTORY FILES (By Category)

### 🚀 DEPLOYMENT SCRIPTS (13 files)

| File | Purpose | Status | Notes |
|------|---------|--------|-------|
| `deploy.sh` | **Main deployment script** | ✅ Active | Primary deployment tool |
| `deploy-to-server.sh` | Generic server deployment | 🟡 Legacy? | Check if still used |
| `deploy-billing-to-production.sh` | Billing feature deployment | 📦 Specific | Sprint-specific |
| `deploy-currency-system.sh` | Currency feature deployment | 📦 Specific | Sprint-specific |
| `deploy-metrics-to-production.sh` | Metrics feature deployment | 📦 Specific | Sprint-specific |
| `deploy-odoo-action-system.sh` | Odoo action system deployment | 📦 Specific | Sprint-specific |
| `deploy-odoo-fixes.sh` | Odoo fixes deployment | 📦 Specific | Sprint-specific |
| `deploy-odoo-template.sh` | Odoo template deployment | 📦 Specific | Sprint-specific |
| `deploy-phase4-to-production.sh` | Phase 4 deployment | 📦 Specific | Sprint-specific |
| `deploy-team-management-to-production.sh` | Team management deployment | 📦 Specific | Sprint-specific |
| `deploy-template-and-autostop-to-production.sh` | Template + autostop deployment | 📦 Specific | Sprint-specific |
| `deploy-template-fix-to-production.sh` | Template fix deployment | 📦 Specific | Sprint-specific |
| `deploy-ui-updates.sh` | UI updates deployment | 📦 Specific | Sprint-specific |

**Recommendation:** Consolidate sprint-specific scripts into `scripts/deployed/` archive

---

### 🧪 TEST FILES (14 files)

#### Test Scripts (Root)
| File | Purpose | Status | Notes |
|------|---------|--------|-------|
| `test_complete_flow.py` | Complete flow test | 🟡 Duplicate | Version 1 |
| `test_complete_flow_v2.py` | Complete flow test v2 | 🟡 Duplicate | Version 2 |
| `test_complete_flow_v3.py` | Complete flow test v3 | 🟡 Duplicate | Version 3 |
| `test_htmx_workspace.py` | HTMX workspace test | ✅ Specific | HTMX feature test |
| `test_mailjet_direct.py` | Mailjet email test | ✅ Specific | Email service test |
| `test_no_username_e2e.py` | No-username E2E test | ✅ Specific | Feature test |
| `test_playwright_registration.py` | Playwright registration test | ✅ Specific | E2E test |
| `test_proof_generation.py` | Proof generation test | ✅ Specific | Feature test |
| `test_workspace_email.py` | Workspace email test | ✅ Specific | Email test |
| `test_sprint1_features.py` | Sprint 1 features test | 📦 Sprint | Sprint-specific |
| `test_sprint1_simple.py` | Sprint 1 simple test | 📦 Sprint | Sprint-specific |
| `test_audit_logging.py` | Audit logging test | ✅ Specific | Security test |

**Recommendation:** Move all to `tests/` directory

#### Test Screenshots/Data
| File | Purpose | Status | Notes |
|------|---------|--------|-------|
| `form_persistence.png` | Form persistence screenshot | 📸 Evidence | Feature screenshot |
| `password_filled.png` | Password filled screenshot | 📸 Evidence | Test screenshot |
| `password_initial.png` | Password initial screenshot | 📸 Evidence | Test screenshot |
| `manual_test_01_register_filled.png` | Manual test screenshot 1 | 📸 Evidence | Test evidence |
| `manual_test_02_after_register.png` | Manual test screenshot 2 | 📸 Evidence | Test evidence |
| `manual_test_03_team_page.png` | Manual test screenshot 3 | 📸 Evidence | Test evidence |
| `production-register-test.png` | Production test screenshot | 📸 Evidence | Production test |
| `test_registration_error.png` | Registration error screenshot | 📸 Evidence | Error screenshot |
| `test_results_live_payment_validation_20251028_065403.json` | Live payment test result | 📊 Data | Test data |

**Recommendation:** Move to `tests/screenshots/` and `tests/data/`

---

### 📚 DOCUMENTATION (18 files)

#### Deployment Docs
| File | Purpose | Status | Notes |
|------|---------|--------|-------|
| `DEPLOYMENT.md` | General deployment guide | ✅ Active | Primary deploy docs |
| `DEPLOYMENT_GUIDE.md` | Deployment guide | 🟡 Duplicate? | Check vs DEPLOYMENT.md |
| `DEPLOYMENT_SUCCESS.md` | Deployment success notes | 📦 Archive | Success report |
| `BILLING_DEPLOYMENT.md` | Billing deployment guide | 📦 Sprint | Sprint-specific |
| `BILLING_PRODUCTION_DEPLOYMENT.md` | Billing production deploy | 📦 Sprint | Sprint-specific |

#### Test/Sprint Reports
| File | Purpose | Status | Notes |
|------|---------|--------|-------|
| `TEST_RESULTS_USERNAME_REMOVAL.md` | Username removal test results | 📦 Archive | Test report |
| `TEST_INFRASTRUCTURE_FIXES.md` | Test infrastructure fixes | 📦 Archive | Fix report |
| `SPRINT1_TEST_REPORT.md` | Sprint 1 test report | 📦 Archive | Sprint report |
| `SPRINT2_DEPLOYMENT.md` | Sprint 2 deployment | 📦 Archive | Sprint report |
| `SPRINT2_QUOTA_INVESTIGATION.md` | Sprint 2 quota investigation | 📦 Archive | Sprint report |
| `SPRINT2_TEST_REPORT.md` | Sprint 2 test report | 📦 Archive | Sprint report |

#### Feature Documentation
| File | Purpose | Status | Notes |
|------|---------|--------|-------|
| `MANUAL_PAYMENT_TEST_GUIDE.md` | Manual payment testing guide | ✅ Active | Payment testing |
| `PAYTR_LIVE_ACTIVE.md` | PayTR live status | ✅ Active | Payment status |
| `ODOO_TEMPLATE_TEST_RESULTS.md` | Odoo template test results | 📦 Archive | Test results |
| `ODOO_TEMPLATE_TEST_STEPS.md` | Odoo template test steps | ✅ Active | Test guide |

#### Project Planning
| File | Purpose | Status | Notes |
|------|---------|--------|-------|
| `MASTER_PLAN.md` | Project master plan | ✅ Active | **IMPORTANT** |
| `LOCAL_DEVELOPMENT.md` | Local development guide | ✅ Active | **IMPORTANT** |
| `README.md` | Project README | ✅ Active | **IMPORTANT** |

**Recommendation:**
- Keep: README.md, MASTER_PLAN.md, LOCAL_DEVELOPMENT.md, DEPLOYMENT.md
- Archive sprint/test reports to `docs/archived-reports/`

---

### ⚙️ CONFIGURATION FILES

| File | Purpose | Status | Notes |
|------|---------|--------|-------|
| `config.py` | Main Flask configuration | ✅ CORE | **CRITICAL** |
| `requirements.txt` | Python dependencies | ✅ CORE | **CRITICAL** |
| `pytest.ini` | Pytest configuration | ✅ CORE | Test config |
| `.gitignore` | Git ignore rules | ✅ CORE | Version control |

---

### 🗄️ DATABASE & SCRIPTS

| File | Purpose | Status | Notes |
|------|---------|--------|-------|
| `run_migrations.py` | Database migration runner | ✅ Active | Migration tool |
| `seed_odoo_production.py` | Odoo production seeder | ✅ Active | Data seeding |
| `seed_odoo_template.sql` | Odoo template SQL | ✅ Active | SQL seed data |
| `workspace_provisioner.db` | SQLite database | 🗄️ Data | Development DB |

---

### 🛠️ UTILITY SCRIPTS

| File | Purpose | Status | Notes |
|------|---------|--------|-------|
| `run_e2e_tests.sh` | E2E test runner | ✅ Active | Test automation |
| `rollback-provisioning-ui.sh` | UI rollback script | ✅ Active | Emergency rollback |

---

### 📦 ARCHIVES & BACKUPS

| File | Purpose | Status | Notes |
|------|---------|--------|-------|
| `youarecoder-deployment.tar.gz` | Deployment archive | 📦 Backup | Deployment backup |
| `traefik-config.tar.gz` | Traefik config archive | 📦 Backup | Config backup |
| `provisioning.html.production.backup.20251114_192114` | HTML backup | 📦 Backup | Recent backup |

---

### 🧹 TEMPORARY/GENERATED FILES

| File | Purpose | Status | Action |
|------|---------|--------|--------|
| `.coverage` | Coverage report data | 🧹 Temp | Ignore in git |
| `htmlcov/` | HTML coverage reports | 🧹 Temp | Ignore in git |
| `__pycache__/` | Python bytecode | 🧹 Temp | Ignore in git |
| `.pytest_cache/` | Pytest cache | 🧹 Temp | Ignore in git |
| `.serena/` | Serena MCP cache | 🧹 Temp | Ignore in git |
| `team_page_full.html` | Temp HTML file | 🧹 Temp | Delete or archive |

---

## 🏗️ CORE DIRECTORIES (Detailed)

### `/app/` - Application Source Code

```
app/
├── __init__.py             Flask app initialization
├── models.py              Database models (48KB - large!)
├── admin.py               Admin panel (35KB - large!)
├── forms.py               WTForms form definitions
├── cli.py                 CLI commands
├── template_form.html     Template form (orphaned?)
├── routes/                Route blueprints
│   ├── admin/            Admin routes
│   ├── auth/             Authentication routes
│   └── workspace/        Workspace routes
├── services/             Business logic services
│   ├── odoo/            Odoo integration
│   ├── payment/         Payment processing
│   └── email/           Email services
├── utils/               Utility functions
├── templates/           Jinja2 templates
└── static/             CSS, JS, images
```

**Issues:**
- `template_form.html` in app root (should be in templates/)
- `models.py` and `admin.py` are very large (consider splitting)

---

### `/tests/` - Test Suite

```
tests/
├── conftest.py                    Pytest configuration
├── test_models.py                 Model tests
├── test_auth_security.py          Auth security tests
├── test_billing_routes.py         Billing route tests
├── test_decorators.py             Decorator tests
├── test_integration.py            Integration tests
├── test_rate_limiting.py          Rate limiting tests
├── test_security_headers.py       Security header tests
├── test_action_executor.py        Action executor tests
├── test_action_handlers.py        Action handler tests
├── test_e2e_comprehensive_features.py  E2E tests
├── test_e2e_paytr_subscription.py     Payment E2E tests
├── test_payment_emails.py         Payment email tests
├── test_paytr_service.py          PayTR service tests
├── test_safe_live_payment_validation.py  Live payment validation
├── test_provisioner.py            Provisioner tests
├── screenshots/                   Test screenshots
└── page_content.txt              Test page content
```

**Well organized!** ✅

---

### `/docs/` - Documentation

```
docs/
├── ADMIN-PLAYBOOK.md             Admin operations guide
├── DAY0-ANALYSIS-REPORT.md       Initial analysis
├── DNS-CONFIGURATION.md          DNS setup guide
├── DNS-STATUS-REPORT.md          DNS status
├── MASTER_PLAN.md                Project plan
├── PLAYWRIGHT-TEST-REPORT.md     Playwright tests
├── SECURITY_INCIDENT_2025-10-27.md  Security incident
├── TROUBLESHOOTING.md            Troubleshooting guide
├── UI-TEST-PLAN.md               UI testing plan
├── USER-GUIDE.md                 User guide
├── security-audit-report.md      Security audit
├── security-implementation-summary.md  Security implementation
├── test-suite-summary.md         Test suite summary
├── daily-reports/                Daily reports
├── e2e-screenshots/              E2E screenshots
└── pdca/                         PDCA cycle docs
```

**Well organized!** ✅

---

## 🎯 CLEANUP RECOMMENDATIONS

### Priority 1: Consolidate Deployment Scripts (13 → 3)

**Keep in root:**
- `deploy.sh` (main deployment)

**Move to `scripts/deployment/`:**
- All sprint-specific deploy scripts

**Archive to `scripts/archived/`:**
- Old/unused deployment scripts

---

### Priority 2: Organize Test Files (14 → 0 in root)

**Move to `tests/`:**
- All `test_*.py` files from root

**Move to `tests/screenshots/`:**
- All `.png` files

**Move to `tests/data/`:**
- `test_results_*.json`

---

### Priority 3: Archive Documentation (18 → 5 in root)

**Keep in root:**
- `README.md`
- `MASTER_PLAN.md`
- `LOCAL_DEVELOPMENT.md`

**Move to `docs/`:**
- `DEPLOYMENT.md`
- `MANUAL_PAYMENT_TEST_GUIDE.md`
- `ODOO_TEMPLATE_TEST_STEPS.md`

**Archive to `docs/archived-reports/`:**
- All sprint reports
- All test result reports
- Duplicate deployment docs

---

### Priority 4: Clean Temporary Files

**Add to `.gitignore` and delete:**
```
.coverage
htmlcov/
*.db (except production backups)
team_page_full.html
```

---

### Priority 5: Organize Utilities

**Create `scripts/` structure:**
```
scripts/
├── deployment/           All deploy-*.sh
├── database/            run_migrations.py, seed_*.py/sql
├── testing/             run_e2e_tests.sh
├── maintenance/         rollback scripts
└── archived/            Old scripts
```

---

## 📊 CLEANUP IMPACT ESTIMATE

| Category | Before | After | Improvement |
|----------|--------|-------|-------------|
| **Root Python files** | 14 | 0 | ✅ -100% |
| **Root shell scripts** | 13 | 1 | ✅ -92% |
| **Root documentation** | 18 | 3 | ✅ -83% |
| **Root screenshots** | 8 | 0 | ✅ -100% |
| **Root total files** | ~70 | ~15 | ✅ -79% |

**Estimated cleanup:** ~55 files organized or archived

---

## ✅ CURRENT STATUS

### Well-Organized ✅
- `/app/` - Good structure (minor issues)
- `/tests/` - Excellent organization
- `/docs/` - Well categorized
- Core config files in place

### Needs Cleanup 🧹
- Root directory cluttered (70+ files)
- Deployment scripts scattered
- Test files in wrong location
- Duplicate documentation

### Critical Files ⚠️
**Never touch:**
- `config.py`
- `requirements.txt`
- `/app/` directory
- `/tests/` directory (location is fine)
- `workspace_provisioner.db` (production data)

---

## 🚀 NEXT STEPS

1. **Review this inventory** - Confirm file purposes
2. **Approve cleanup plan** - Choose priority levels
3. **Execute cleanup** - Systematic file organization
4. **Update documentation** - Reflect new structure
5. **Add to `.gitignore`** - Prevent future clutter

---

**Questions?**
- Which deployment scripts are still in active use?
- Are sprint reports needed for reference?
- Should we consolidate the three `test_complete_flow` versions?
- Any files you specifically want to keep in root?
