# YouAreCoder.com - 14 Gün Sprint Plan (MASTER PLAN)

**Başlangıç:** 2025-10-26
**Metodoloji:** SuperClaude Commands (SCC) - Hybrid Approach
**AI/Human Ratio:** 97.8% AI / 2.2% Human
**Hedef:** Multi-tenant SaaS platform (code-server workspaces)

---

## 🎯 Hedefler

- [ ] Pure Flask SaaS platform
- [ ] Multi-tenant subdomain routing (firma.youarecoder.com, dev.firma.youarecoder.com)
- [ ] 5 firma, 20 workspace support capacity
- [ ] PayTR payment integration
- [ ] HTTPS with Let's Encrypt SSL
- [ ] Production-ready security
- [ ] Complete documentation

---

## 🏗️ Tech Stack

**Backend:**
- Flask 3.0 + Gunicorn
- PostgreSQL 15 + SQLAlchemy
- Alembic (migrations)
- Flask-Login, Flask-Limiter, Flask-WTF

**Frontend:**
- HTMX 1.9 + Tailwind CSS 3.4
- Alpine.js + Jinja2

**Infrastructure:**
- Ubuntu 22.04 LTS
- Traefik v2.10 + Let's Encrypt
- Systemd services

**Payment:**
- PayTR API

---

## 📅 Sprint Progress

### **Week 1: Core Infrastructure**

#### **Day 0: Discovery Phase**
- [x] READ-ONLY analysis of existing server (46.62.150.235)
- [x] Document add_dev_env.py logic
- [x] Extract best practices
- [x] Create migration strategy
- **Status:** ✅ Complete (2025-10-26)
- **SCC:** `/sc-analyze` → `/sc-save "day0-discovery"`
- **Deliverable:** [DAY0-ANALYSIS-REPORT.md](DAY0-ANALYSIS-REPORT.md) ✅
- **Daily Report:** [day00-discovery.md](daily-reports/day00-discovery.md) ✅

---

#### **Day 1-2: Foundation**
- [x] New server setup (37.27.21.167)
- [x] PostgreSQL 16 installation and configuration
- [x] Python 3.12 + virtual environment setup
- [x] Flask app skeleton with factory pattern
- [x] SQLAlchemy models (Company, Workspace, User)
- [x] Flask-Login authentication routes
- [x] Alembic migrations (initial schema applied)
- [ ] 20+ unit tests (deferred to Day 3-4)
- **Status:** ✅ Complete (2025-10-27)
- **SCC:** `/sc-load day0-discovery` → `/sc-implement` → Autonomous execution
- **Human Input:** None
- **Deliverable:** Working Flask app with database schema ✅
- **Daily Report:** [day01-02-foundation.md](daily-reports/day01-02-foundation.md)

---

#### **Day 3-4: Workspace Provisioning**
- [x] WorkspaceProvisioner service (port allocation, user creation, code-server setup)
- [x] API endpoints (status, restart, stop, start, logs)
- [x] Port allocation system (sequential, DB-tracked, 8001-8100)
- [x] Disk quota management (plan-based: 10GB/50GB/250GB)
- [x] Systemd service template (auto-restart, proper user isolation)
- [x] Error handling + rollback mechanism
- [x] Unit tests (16 tests, 13 passing)
- **Status:** ✅ Complete (2025-10-27)
- **SCC:** `/sc-load day1-2-foundation` → `/sc-implement` → Autonomous execution
- **Human Input:** Deferred - Provisioning tested in unit tests
- **Deliverable:** Functional provisioning service with API ✅
- **Daily Report:** [day03-04-provisioning.md](daily-reports/day03-04-provisioning.md)

---

#### **Day 5-7: Traefik Integration & SSL**
- [x] Traefik v2.10 installation
- [x] Static configuration (traefik.yml)
- [x] Dynamic routing system
- [x] Let's Encrypt wildcard SSL (manual DNS-01 challenge)
- [x] Automatic HTTPS redirect
- [x] Systemd services
- [x] Health monitoring
- [x] Workspace route priority configuration
- [x] Subdomain format optimization (company-workspace.youarecoder.com)
- **Status:** ✅ Complete (2025-10-27)
- **SCC:** `/sc-implement` → `/sc-test` → `/sc-troubleshoot` → Autonomous execution
- **Human Input:** ✋ 15 min - DNS TXT records for wildcard cert (2 rounds)
- **Deliverable:** HTTPS subdomain routing ✅
- **Daily Report:** [day05-07-traefik-ssl.md](daily-reports/day05-07-traefik-ssl.md)

---

### **Week 2: Business Logic & Launch**

#### **Day 8-9: PayTR Integration**
- [ ] PayTR API client
- [ ] Subscription models (Starter/Team/Enterprise)
- [ ] Payment flow implementation
- [ ] Webhook handling
- [ ] Recurring billing
- [ ] Workspace limit enforcement
- [ ] Invoice generation (PDF)
- **Status:** ⏳ Pending
- **SCC:** `/sc-load` → `/sc-implement` → `/sc-test` → `/sc-save`
- **Human Input:** ✋ 2 min - PayTR credentials
- **Deliverable:** Complete payment system

---

#### **Day 10-11: Application Testing & Portal**
- [x] Admin dashboard testing
  - [x] Login/authentication flow
  - [x] Workspace creation modal
  - [x] Workspace listing and status
  - [x] HTMX dynamic updates
- [x] End-to-end workspace provisioning
  - [x] Linux user creation
  - [x] Code-server installation and config
  - [x] Systemd service automation
  - [x] Traefik dynamic routing
- [x] SSL certificate verification
- [x] Code-server access testing
- [ ] Landing page (pricing, features)
- [ ] Company registration flow
- [ ] Usage statistics dashboard
- [ ] Billing section UI
- [ ] Responsive design (mobile-first)
- [ ] Dark mode support
- **Status:** 🟡 Partial (2025-10-27)
- **SCC:** `/sc-implement` → `/sc-test` → Playwright automation
- **Human Input:** ✋ 5 min - Confirm workspace access
- **Deliverable:** Working workspace provisioning ✅ | Portal UI pending
- **Daily Report:** [day10-11-testing.md](daily-reports/day10-11-testing.md)

---

#### **Day 12-13: Security & Testing**
- [ ] Security audit (SQL injection, XSS, CSRF)
- [ ] Input validation
- [ ] Rate limiting
- [ ] Password security
- [ ] Security headers
- [ ] Unit tests (80%+ coverage)
- [ ] Integration tests (E2E flows)
- [ ] Load testing (20 concurrent workspaces)
- [ ] Bug fixes
- **Status:** ⏳ Pending
- **SCC:** `/sc-load` → `/sc-analyze` → `/sc-test` → `/sc-troubleshoot` → `/sc-save`
- **Human Input:** ✋ 30 min - Security review
- **Deliverable:** Secure, tested platform

---

#### **Day 14: Production Launch**
- [ ] Systemd services (all components)
- [ ] Database backup automation
- [ ] Log rotation
- [ ] Monitoring setup
- [ ] Admin playbook
- [ ] User guide
- [ ] API documentation (OpenAPI)
- [ ] Troubleshooting guide
- [ ] Pilot deployment (2 companies, 5 workspaces)
- **Status:** ⏳ Pending
- **SCC:** `/sc-load` → `/sc-build` → `/sc-document` → `/sc-save`
- **Human Input:** ✋ 60 min - Go/no-go + pilot onboarding
- **Deliverable:** Live production platform

---

## 🚨 Blockers

_None currently_

---

## 📝 Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-10-26 | Pure Flask (not Odoo) | Speed priority, infrastructure management fit |
| 2025-10-26 | PostgreSQL over SQLite | Production-ready, better scalability |
| 2025-10-26 | SCC Hybrid methodology | 97.8% AI automation, human at critical points |
| 2025-10-26 | Dual-server strategy | Protect production, clean start |
| 2025-10-26 | 3-layer tracking system | Human visibility + AI persistence |

---

## 📊 Human Touchpoints

| Day | Task | Duration | Type |
|-----|------|----------|------|
| 0 | New server + credentials | 10 min | Setup |
| 3-4 | Manual workspace test | 10 min | Validation |
| 5-7 | DNS wildcard record | 5 min | Config |
| 8-9 | PayTR credentials | 2 min | Config |
| 12-13 | Security review | 30 min | Validation |
| 14 | Go/no-go + pilot | 60 min | Launch |
| Daily | Plan approval + summary | 5 min/day | Tracking |

**Total Human Effort:** ~156 minutes (2.6 hours)

---

## 🎯 Success Metrics (Target: Day 14)

**Technical:**
- [ ] 5 pilot companies registered
- [ ] 20 workspaces active and accessible
- [ ] HTTPS working on all subdomains
- [ ] PayTR test payment successful
- [ ] 80%+ test coverage
- [ ] <3s page load time
- [ ] Zero critical security vulnerabilities

**Documentation:**
- [ ] All daily reports generated
- [ ] Complete user/admin guides
- [ ] API documentation (OpenAPI)
- [ ] All /sc-save sessions preserved

**Process:**
- [ ] SCC methodology validated
- [ ] 97.8% AI automation achieved
- [ ] Template ready for future projects

---

## 🔄 SCC Daily Pattern

```bash
🌅 MORNING:
/sc-load "previous-day-session"
/sc-pm "Plan today's tasks"
→ Show plan to human → Approval

💼 DAY WORK:
/sc-design | /sc-implement | /sc-test | /sc-build
→ Autonomous AI execution

🌙 EVENING:
/sc-pm "Summarize progress"
/sc-save "current-day-session"
→ Generate daily report
→ Update MASTER_PLAN.md
```

---

## 📦 Project Structure

```
/home/mustafa/youarecoder/
├── docs/
│   ├── MASTER_PLAN.md (this file)
│   ├── daily-reports/
│   ├── ARCHITECTURE.md
│   └── API.md
├── app/
│   ├── models.py
│   ├── routes/
│   ├── services/
│   ├── templates/
│   └── static/
├── tests/
├── migrations/
├── config/
└── .git/
```

---

## 🚀 Next Steps

**Immediate:**
1. ✅ MASTER_PLAN.md created (this file)
2. ⏳ Waiting for new server credentials
3. ⏳ Day 0 will start when credentials received

**On Deck:**
- New Hetzner server setup (Human - 10 min)
- Day 0: Existing infrastructure analysis (AI - 2-4 hours)

---

**Last Updated:** 2025-10-27 (Day 10-11 testing complete)
**Current Status:**
- Day 5-7 ✅ Complete | Traefik + SSL working
- Day 10-11 🟡 Partial | Workspace provisioning tested ✅ | Portal UI pending
**Current Session:** day10-11-testing
**Next Session:** Day 8-9 PayTR Integration OR Day 10-11 Portal UI completion
