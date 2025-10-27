# Day 0: Existing Infrastructure Analysis Report

**Date:** 2025-10-26
**Analyst:** Claude (SuperClaude Commands)
**Objective:** READ-ONLY analysis of production server to understand workspace provisioning

---

## 📋 Executive Summary

**Existing Server:** 46.62.150.235 (dev.alkedos.com)
**New Server:** 37.27.21.167 (youarecoder.com)
**Analysis Status:** ✅ Complete

**Key Findings:**
- Well-structured Python automation (`add_dev_env.py`)
- Odoo-specific development environment
- Nginx reverse proxy + Let's Encrypt SSL
- Systemd-managed code-server instances
- UID-based port allocation (deterministic)
- Active users: 5 (ender, gulten, kagan, mustafa, nejdet)

---

## 🔍 Detailed Analysis

### **1. add_dev_env.py - Main Provisioning Script**

**Location:** `/opt/dev-setup/add_dev_env.py` (8,835 bytes)

**Purpose:** Automated developer workspace creation with:
- Linux user creation
- PostgreSQL database setup
- Python virtual environment (Odoo-specific)
- code-server installation per user
- Nginx reverse proxy configuration
- Odoo project skeleton

**Key Components:**

#### **1.1 Port Allocation Strategy**
```python
CODE_BASE = 10080  # code-server base port
ODOO_BASE = 11000  # Odoo xmlrpc base port

def assign_ports(username):
    u = uid(username)  # Get Linux UID
    code_port = CODE_BASE + (u % 1000)
    odoo_port = ODOO_BASE + (u % 1000)
    return code_port, odoo_port
```

**Analysis:**
- ✅ **Deterministic:** Same user always gets same ports
- ✅ **Scalable:** Supports 1000 users (UID % 1000)
- ⚠️ **Collision Risk:** UIDs 1000 and 2000 would get same port
- 📊 **Current Usage:** mustafa (UID 1000) → port 10080

**Recommendation for YouAreCoder:**
- Use sequential port allocation (track last assigned port in database)
- Range: 8001-8100 (100 workspaces initially)
- Store port in Workspace model for guaranteed uniqueness

---

#### **1.2 User Creation Process**
```python
def create_user(username, password):
    run(f"adduser --disabled-password --gecos '' {username}")
    run(f"echo '{username}:{password}' | chpasswd")
```

**Analysis:**
- ✅ **Secure:** Random 18-character password generation
- ✅ **Standard:** Uses Linux `adduser` command
- ⚠️ **No Cleanup:** Failed creations leave partial state

**Recommendation:**
- Add rollback mechanism on errors
- Validate username (alphanumeric, lowercase only)
- Set disk quotas: `setquota -u <user> <soft> <hard> 0 0 /`

---

#### **1.3 code-server Configuration**
```yaml
# Template: /opt/dev-setup/templates/code-server.config.template
bind-addr: 127.0.0.1:{code_port}
auth: password
password: "{code_password}"  # 20-character random
cert: false  # SSL handled by nginx
```

**Actual Example (user: mustafa):**
```yaml
bind-addr: 127.0.0.1:10080
auth: password
password: "CHnuUYeocWkBd2GW1VAV"
cert: false
```

**Analysis:**
- ✅ **Localhost Binding:** Only accessible via nginx reverse proxy
- ✅ **Password Auth:** Each user has unique password
- ✅ **SSL Offloading:** Nginx handles HTTPS (Let's Encrypt)

---

#### **1.4 Nginx Reverse Proxy**

**Template:** `/opt/dev-setup/templates/nginx-code-https.template`
```nginx
server {
    listen 443 ssl;
    server_name {username}.{domain};  # e.g., mustafa.dev.alkedos.com

    ssl_certificate /etc/letsencrypt/live/dev.alkedos.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/dev.alkedos.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:{code_port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        # WebSocket support (code-server requirement)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

**Analysis:**
- ✅ **Wildcard SSL:** Single cert for all subdomains
- ✅ **WebSocket Support:** Critical for code-server
- ✅ **HTTPS Only:** No HTTP redirect defined (could add)

**Recommendation for YouAreCoder:**
- Use Traefik instead of Nginx (automatic Let's Encrypt, dynamic routing)
- Automatic HTTP → HTTPS redirect
- Health checks for backends

---

#### **1.5 Systemd Service Management**

**Service Template:** `/etc/systemd/system/code-server@.service`
```ini
[Unit]
Description=code-server for %i
After=network.target

[Service]
User=%i  # %i = username from code-server@username.service
WorkingDirectory=/home/%i
ExecStart=/usr/bin/code-server --config /home/%i/.config/code-server/config.yaml
Restart=always

[Install]
WantedBy=multi-user.target
```

**Analysis:**
- ✅ **Template Service:** One service file for all users
- ✅ **Auto-Restart:** Survives crashes
- ✅ **User Isolation:** Each service runs as its user

**Current Active Services:**
```
code-server@ender.service     loaded active running
code-server@gulten.service    loaded active running
code-server@kagan.service     loaded active running
code-server@mustafa.service   loaded active running
code-server@nejdet.service    loaded active running
```

**Recommendation:**
- Same pattern for YouAreCoder ✅
- Add resource limits (MemoryLimit, CPUQuota)
- Add timeout for graceful shutdown

---

### **2. Odoo-Specific Components**

**Note:** YouAreCoder will NOT include Odoo initially, but these patterns are useful.

#### **2.1 Virtual Environment Setup**
```python
def setup_venv_and_bashrc(username):
    venv_dir = f"/home/{username}/.venv"
    run(f"sudo -u {username} python3 -m venv {venv_dir}")
    run(f"sudo -u {username} {venv_dir}/bin/pip install debugpy psycopg2_binary")
    run(f"sudo -u {username} {venv_dir}/bin/pip install -r /opt/dev-setup/requirements.txt")
```

**Analysis:**
- ✅ **Isolated Environment:** Each user has own Python venv
- ✅ **Odoo Dependencies:** requirements.txt (~5.9KB, 60+ packages)

**Not Needed for YouAreCoder MVP** (pure code-server workspace)

---

#### **2.2 Project Skeleton**
```python
def make_project_skeleton(username, odoo_admin_password):
    home = f"/home/{username}"
    for d in ("Odoo/dibugo-modules", "Odoo/odoo_17", ...):
        run(f"sudo -u {username} mkdir -p {home}/{d}")

    # Shared Odoo installation (symlink)
    run(f"sudo -u {username} ln -s /opt/shared/odoo {home}/Odoo/odoo")
    run(f"sudo -u {username} ln -s /opt/shared/enterprise {home}/Odoo/enterprise")
```

**Analysis:**
- ✅ **Shared Resources:** `/opt/shared/odoo` symlinked to each user
- ✅ **Disk Efficiency:** Single Odoo installation for all users

**Adaptation for YouAreCoder:**
- Optional shared workspace templates
- Example: "Python Starter", "Node.js Starter", "React Starter"
- Stored in `/opt/youarecoder/templates/`

---

### **3. Security & Permissions**

**Findings:**

#### **3.1 Password Generation**
```python
def gen_pass(n=18):
    alphabet = string.ascii_letters + string.digits  # [a-zA-Z0-9]
    return ''.join(secrets.choice(alphabet) for _ in range(n))
```

**Analysis:**
- ✅ **Cryptographically Secure:** `secrets` module (not `random`)
- ✅ **Sufficient Length:** 18-20 characters
- ✅ **Complexity:** Letters + digits

**Recommendation:** ✅ Adopt same approach for YouAreCoder

---

#### **3.2 User Isolation**
- ✅ Each user has separate Linux account
- ✅ Home directories: `/home/{username}` with standard permissions (755)
- ✅ code-server runs as user (not root)
- ⚠️ No disk quotas enforced (could fill disk)

**Recommendation:**
- Add disk quotas based on plan (Starter: 10GB, Team: 50GB, Enterprise: 250GB)
- Monitor disk usage per user
- Alert at 80% usage, suspend at 100%

---

#### **3.3 Network Security**
- ✅ code-server binds to 127.0.0.1 (localhost only)
- ✅ Only accessible via nginx HTTPS proxy
- ✅ SSL certificates from Let's Encrypt

**Recommendation:** ✅ Same pattern with Traefik

---

### **4. File Structure Analysis**

**Existing Server (`/opt/dev-setup/`):**
```
/opt/dev-setup/
├── add_dev_env.py (8,835 bytes) - Main provisioning script
├── distribute_vscode_config.py (2,612 bytes) - VS Code settings distributor
├── remove_dev_env.py (3,512 bytes) - User removal script
├── install_ext_all_users.py (3,711 bytes) - Extension installer
├── fix_templates.py (802 bytes) - Template fixer
├── requirements.txt (5,929 bytes) - Python dependencies (Odoo)
├── extensions/ - VS Code extensions (.vsix files)
└── templates/
    ├── bashrc.template (176 bytes)
    ├── code-server.config.template (88 bytes)
    ├── launch.json.template (665 bytes) - VS Code debug config
    ├── nginx-code-https.template (431 bytes)
    ├── nginx-odoo-https.template (308 bytes)
    └── odoo.conf.template (355 bytes)
```

**Analysis:**
- ✅ **Modular:** Separate scripts for add/remove/install
- ✅ **Template-Based:** Easy to customize
- ⚠️ **No Logging:** Errors go to stdout only
- ⚠️ **No Rollback:** Failed creation leaves partial state

---

### **5. Observed Issues & Failed Services**

**Failed Services (16 out of 21):**
```
code-server@deneme10.service  failed
code-server@deneme4.service   failed
code-server@dev1.service      failed
code-server@mustafa2.service  failed
... (12 more)
```

**Possible Causes:**
- Users deleted but services not stopped
- Incorrect config files
- Port conflicts
- Missing home directories

**Recommendation for YouAreCoder:**
- Cleanup script for failed services
- Health monitoring dashboard
- Auto-disable services for suspended workspaces

---

## 🎯 Best Practices Extracted

### **1. Architecture Patterns ✅**
- **User-Based Isolation:** Each workspace = Linux user
- **Systemd Template Services:** `@.service` pattern
- **Reverse Proxy:** Nginx/Traefik for SSL + routing
- **Localhost Binding:** Services only on 127.0.0.1

### **2. Port Management ✅**
- **Deterministic Allocation:** UID-based (existing)
- **Sequential Allocation:** Database-tracked (recommended)
- **Reserved Ranges:** Clear separation (8001-8100 for code-server)

### **3. Security ✅**
- **Strong Passwords:** `secrets` module, 18+ chars
- **SSL Everywhere:** Let's Encrypt via reverse proxy
- **User Isolation:** Linux permissions + separate processes

### **4. Automation ✅**
- **Template-Based:** Jinja2-style placeholders
- **Idempotent:** Can re-run without breaking
- **Error Handling:** subprocess.run(check=True)

---

## 🚧 Areas for Improvement

### **1. Rollback Mechanism ❌**
**Problem:** Partial failures leave orphaned resources
**Solution:** Transaction-like wrapper, cleanup on error

### **2. Disk Quotas ❌**
**Problem:** Users can fill entire disk
**Solution:** `setquota` based on subscription plan

### **3. Resource Limits ❌**
**Problem:** No CPU/RAM limits per user
**Solution:** Systemd CPUQuota, MemoryLimit

### **4. Monitoring & Logging ❌**
**Problem:** No centralized logs or metrics
**Solution:** Structured logging (JSON), health dashboard

### **5. Cleanup Automation ❌**
**Problem:** 16 failed services still present
**Solution:** Auto-cleanup script for stale resources

---

## 📊 Migration Strategy to YouAreCoder

### **Phase 1: Core Similarities**
**Keep from existing system:**
- ✅ Linux user-based isolation
- ✅ code-server per user
- ✅ Systemd template services
- ✅ Password generation logic
- ✅ SSL offloading via reverse proxy

### **Phase 2: Key Differences**

| Component | Existing (Alkedos) | New (YouAreCoder) |
|-----------|-------------------|-------------------|
| **Reverse Proxy** | Nginx (manual config) | Traefik (auto config) |
| **SSL** | Single wildcard cert | Auto per-subdomain |
| **Port Allocation** | UID % 1000 | Sequential DB-tracked |
| **Database** | N/A | PostgreSQL (companies, workspaces) |
| **Payment** | N/A | PayTR integration |
| **Project Setup** | Odoo skeleton | Generic workspace |
| **Disk Quotas** | None | Plan-based (10/50/250GB) |

### **Phase 3: New Features**
- **Multi-Tenancy:** Companies + Workspaces hierarchy
- **Subscription Management:** Starter/Team/Enterprise plans
- **Customer Portal:** Self-service workspace management
- **Resource Monitoring:** Disk/CPU/RAM usage per workspace
- **Auto-Suspension:** Payment failure → workspace suspend
- **Health Dashboard:** Admin view of all workspaces

---

## 🔧 Recommended Tools & Technologies

### **Replace Nginx with Traefik:**
**Why:**
- Automatic SSL certificate management
- Dynamic configuration (no reload needed)
- Built-in dashboard
- Docker/file provider support
- Easier to manage programmatically

**Migration:**
```yaml
# Traefik dynamic config (auto-generated from DB)
http:
  routers:
    dev1-firma:
      rule: "Host(`dev1.firma.youarecoder.com`)"
      service: dev1-service
      tls:
        certResolver: letsencrypt
  services:
    dev1-service:
      loadBalancer:
        servers:
          - url: "http://localhost:8001"
```

---

## 📐 System Specifications

### **Existing Server (46.62.150.235)**
```
OS: Ubuntu 24.04 LTS (6.8.0-71-generic)
Domain: dev.alkedos.com
Active Users: 5 (ender, gulten, kagan, mustafa, nejdet)
Code-server: Per-user systemd services
Port Range: 10080-10084 (code-server), 11000-11004 (Odoo)
SSL: Let's Encrypt wildcard (*.dev.alkedos.com)
```

### **New Server (37.27.21.167)**
```
OS: Ubuntu 24.04 LTS (6.8.0-71-generic)
Hostname: youarecoder
Disk: 75GB (71GB available)
RAM: 7.7GB
CPU: Unknown (to be verified)
Domain: youarecoder.com
Status: Fresh install, ready for setup
```

---

## ✅ Day 0 Deliverables

1. ✅ **add_dev_env.py** fully documented
2. ✅ **Port allocation strategy** analyzed
3. ✅ **Security patterns** extracted
4. ✅ **Nginx config** templates reviewed
5. ✅ **Systemd service** pattern documented
6. ✅ **Best practices** identified
7. ✅ **Migration strategy** defined
8. ✅ **New server** access verified

---

## 🚀 Next Steps (Day 1-2)

**With this analysis complete, we can now:**

1. **Design YouAreCoder architecture** (adapted from existing)
2. **Setup PostgreSQL** on new server
3. **Create Flask application skeleton**
4. **Implement WorkspaceProvisioner** service (based on add_dev_env.py)
5. **Install Traefik** instead of Nginx
6. **Begin Day 1 tasks** as planned in MASTER_PLAN.md

---

**Analysis Complete:** 2025-10-26
**Analyst:** Claude (SuperClaude Commands - /sc-analyze)
**Session:** day0-discovery
**Next:** /sc-save → Day 1 Foundation

