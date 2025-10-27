# YouAreCoder Admin Playbook

**Version:** 1.0
**Last Updated:** 2025-10-27
**Target Audience:** System Administrators, DevOps Engineers

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Daily Operations](#daily-operations)
3. [Common Tasks](#common-tasks)
4. [Troubleshooting](#troubleshooting)
5. [Monitoring](#monitoring)
6. [Backup & Recovery](#backup--recovery)
7. [Security](#security)
8. [Emergency Procedures](#emergency-procedures)

---

## System Overview

### Architecture
```
Internet
    ↓
Traefik (Port 80/443)
    ├─→ Flask App (Port 5000) → PostgreSQL (Port 5432)
    └─→ Code-Server Workspaces (Ports 8001-8100)
```

### Server Details
- **Production Server:** 37.27.21.167
- **Domain:** youarecoder.com
- **OS:** Ubuntu 22.04 LTS
- **Users:** root (primary admin)

### Installed Services
| Service | Status Command | Config Location |
|---------|---------------|-----------------|
| Traefik | `systemctl status traefik` | `/etc/traefik/` |
| Flask App | `systemctl status youarecoder` | `/root/youarecoder/` |
| PostgreSQL | `systemctl status postgresql` | `/etc/postgresql/` |

---

## Daily Operations

### Morning Health Check
```bash
# Run comprehensive health check
/root/youarecoder/scripts/health-check.sh

# Check service status
systemctl status youarecoder traefik postgresql

# Review overnight logs
tail -100 /var/log/youarecoder/error.log
tail -100 /var/log/traefik/traefik.log
```

### Monitor Key Metrics
```bash
# Disk space
df -h

# Memory usage
free -h

# Active workspaces
ps aux | grep code-server | wc -l

# Database connections
sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity;"
```

### Review Backups
```bash
# List recent backups
ls -lh /var/backups/youarecoder/database/

# Verify latest backup
ls -lh /var/backups/youarecoder/database/youarecoder_$(date +%Y%m%d)*.sql.gz

# Check backup log
tail -50 /var/log/youarecoder/backup.log
```

---

## Common Tasks

### 1. Application Deployment

**Pull Latest Changes:**
```bash
cd /root/youarecoder
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
```

**Database Migrations:**
```bash
cd /root/youarecoder
source venv/bin/activate

# Create migration (if schema changed)
# flask db migrate -m "description"

# Apply migrations
# flask db upgrade
```

**Restart Services:**
```bash
systemctl restart youarecoder
systemctl restart traefik  # Only if Traefik config changed
```

**Verify Deployment:**
```bash
# Check service status
systemctl status youarecoder

# Test endpoint
curl -I https://youarecoder.com

# Check logs for errors
journalctl -u youarecoder -n 50 --no-pager
```

### 2. User Management

**Create New Company:**
```bash
cd /root/youarecoder
source venv/bin/activate
python3 << EOF
from app import create_app
from app.models import Company, User, db
import secrets

app = create_app()
with app.app_context():
    # Create company
    company = Company(
        name="Company Name",
        subdomain="companyslug",
        plan="starter",
        max_workspaces=1
    )
    db.session.add(company)

    # Create admin user
    user = User(
        email="admin@company.com",
        username="admin",
        full_name="Admin Name",
        company_id=company.id,
        role="admin"
    )
    password = secrets.token_urlsafe(16)
    user.set_password(password)
    db.session.add(user)

    db.session.commit()
    print(f"Company created: {company.subdomain}.youarecoder.com")
    print(f"Admin username: {user.username}")
    print(f"Admin password: {password}")
EOF
```

**Reset User Password:**
```bash
cd /root/youarecoder
source venv/bin/activate
python3 << EOF
from app import create_app
from app.models import User, db
import secrets

app = create_app()
with app.app_context():
    user = User.query.filter_by(email="user@example.com").first()
    if user:
        new_password = secrets.token_urlsafe(16)
        user.set_password(new_password)
        user.failed_login_attempts = 0
        user.account_locked_until = None
        db.session.commit()
        print(f"Password reset for: {user.email}")
        print(f"New password: {new_password}")
    else:
        print("User not found")
EOF
```

### 3. Workspace Management

**List All Workspaces:**
```bash
cd /root/youarecoder
source venv/bin/activate
python3 << EOF
from app import create_app
from app.models import Workspace

app = create_app()
with app.app_context():
    workspaces = Workspace.query.all()
    for ws in workspaces:
        print(f"{ws.subdomain} | Port: {ws.port} | Status: {ws.status}")
EOF
```

**Restart Workspace:**
```bash
# Find workspace service name
systemctl list-units | grep code-server

# Restart specific workspace
systemctl restart code-server@<username>
```

**Check Workspace Disk Usage:**
```bash
# All workspaces
du -sh /home/yac_*

# Specific workspace
du -sh /home/yac_<workspace_name>
```

### 4. SSL Certificate Management

**Check Certificate Status:**
```bash
# View certificate details
echo | openssl s_client -servername youarecoder.com -connect youarecoder.com:443 2>/dev/null | openssl x509 -noout -dates

# Check Traefik ACME log
tail -50 /var/log/traefik/traefik.log | grep -i acme
```

**Force Certificate Renewal:**
```bash
# Traefik auto-renews 30 days before expiry
# To force renewal, restart Traefik
systemctl restart traefik

# Monitor renewal
journalctl -u traefik -f
```

---

## Troubleshooting

### Service Won't Start

**Flask App:**
```bash
# Check detailed error
journalctl -u youarecoder -n 50 --no-pager

# Common issues:
# 1. Database connection
sudo -u postgres psql -l  # Test DB access

# 2. Port already in use
ss -tlnp | grep 5000

# 3. Python dependencies
cd /root/youarecoder && source venv/bin/activate && pip list
```

**Traefik:**
```bash
# Check config syntax
traefik --configFile=/etc/traefik/traefik.yml --dry-run

# Check certificate issues
ls -l /etc/traefik/acme.json
chmod 600 /etc/traefik/acme.json  # Fix permissions

# View detailed logs
journalctl -u traefik -n 100 --no-pager
```

### Database Issues

**Connection Errors:**
```bash
# Check PostgreSQL status
systemctl status postgresql

# Test connection
sudo -u postgres psql -c "SELECT version();"

# Check connections
sudo -u postgres psql -c "SELECT * FROM pg_stat_activity;"

# Restart if needed
systemctl restart postgresql
```

**High Disk Usage:**
```bash
# Check database size
sudo -u postgres psql -c "
SELECT pg_database.datname,
       pg_size_pretty(pg_database_size(pg_database.datname))
FROM pg_database;"

# Vacuum database
sudo -u postgres psql youarecoder -c "VACUUM FULL ANALYZE;"
```

### Performance Issues

**High CPU:**
```bash
# Identify processes
top -o %CPU

# Check Gunicorn workers
ps aux | grep gunicorn

# Review application logs
tail -100 /var/log/youarecoder/error.log | grep -i error
```

**High Memory:**
```bash
# Memory breakdown
free -h
ps aux --sort=-%mem | head -20

# Restart services to clear memory
systemctl restart youarecoder
```

**Slow Responses:**
```bash
# Check database queries
sudo -u postgres psql youarecoder -c "
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE state != 'idle' ORDER BY duration DESC;"

# Review access logs
tail -100 /var/log/youarecoder/access.log | grep -E "slow|timeout"
```

---

## Monitoring

### Automated Health Checks
```bash
# View health check results
cat /var/log/youarecoder/health-check.log | tail -50

# Run manual check
/root/youarecoder/scripts/health-check.sh

# Health check runs every 5 minutes via cron
crontab -l | grep health-check
```

### Log Monitoring
```bash
# Real-time application logs
tail -f /var/log/youarecoder/error.log

# Real-time Traefik logs
tail -f /var/log/traefik/access.log

# Search for errors
grep -i error /var/log/youarecoder/error.log | tail -50
```

### Metrics
```bash
# Active sessions
cd /root/youarecoder && source venv/bin/activate && python3 << EOF
from app import create_app
from app.models import User, Workspace

app = create_app()
with app.app_context():
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    total_workspaces = Workspace.query.count()
    active_workspaces = Workspace.query.filter_by(status='active').count()

    print(f"Users: {active_users}/{total_users} active")
    print(f"Workspaces: {active_workspaces}/{total_workspaces} active")
EOF
```

---

## Backup & Recovery

### Manual Backup
```bash
# Create immediate backup
/root/youarecoder/scripts/backup-database.sh

# List backups
ls -lh /var/backups/youarecoder/database/

# Copy backup offsite
scp /var/backups/youarecoder/database/youarecoder_*.sql.gz user@backup-server:/backups/
```

### Database Restore
```bash
# ⚠️  CRITICAL: This will overwrite current database!

# 1. List available backups
ls -lh /var/backups/youarecoder/database/

# 2. Run restore script (with confirmation)
/root/youarecoder/scripts/restore-database.sh /var/backups/youarecoder/database/youarecoder_YYYYMMDD_HHMMSS.sql.gz

# 3. Verify application
curl -I https://youarecoder.com
```

### Backup Strategy
- **Frequency:** Daily at 2:00 AM (automated)
- **Retention:** 30 days
- **Location:** `/var/backups/youarecoder/database/`
- **Verification:** Automated integrity check after backup
- **Offsite:** Manual SCP recommended weekly

---

## Security

### Update System Packages
```bash
# Update package list
apt update

# Upgrade packages (test in staging first!)
apt upgrade -y

# Restart services if needed
systemctl restart youarecoder traefik postgresql
```

### Review Security Logs
```bash
# Failed login attempts
cd /root/youarecoder && source venv/bin/activate && python3 << EOF
from app import create_app
from app.models import LoginAttempt
from datetime import datetime, timedelta

app = create_app()
with app.app_context():
    failed = LoginAttempt.query.filter_by(success=False).filter(
        LoginAttempt.timestamp > datetime.utcnow() - timedelta(days=1)
    ).count()
    print(f"Failed logins (last 24h): {failed}")
EOF

# System auth logs
tail -100 /var/log/auth.log | grep -i failed
```

### SSL Certificate Audit
```bash
# Check SSL Labs rating (external)
# Visit: https://www.ssllabs.com/ssltest/analyze.html?d=youarecoder.com

# Verify certificate chain
openssl s_client -showcerts -servername youarecoder.com -connect youarecoder.com:443 < /dev/null
```

---

## Emergency Procedures

### Complete System Failure

1. **Verify services down:**
   ```bash
   systemctl status youarecoder traefik postgresql
   ```

2. **Check system logs:**
   ```bash
   journalctl -p err -n 100 --no-pager
   dmesg | tail -50
   ```

3. **Restart services in order:**
   ```bash
   systemctl restart postgresql
   sleep 5
   systemctl restart youarecoder
   systemctl restart traefik
   ```

4. **Verify recovery:**
   ```bash
   /root/youarecoder/scripts/health-check.sh
   curl -I https://youarecoder.com
   ```

### Database Corruption

1. **Stop application:**
   ```bash
   systemctl stop youarecoder
   ```

2. **Attempt PostgreSQL repair:**
   ```bash
   sudo -u postgres pg_dumpall > /tmp/backup_before_repair.sql
   sudo -u postgres reindexdb --all
   ```

3. **If repair fails, restore from backup:**
   ```bash
   /root/youarecoder/scripts/restore-database.sh /var/backups/youarecoder/database/youarecoder_latest.sql.gz
   ```

### Disk Space Emergency

1. **Immediate cleanup:**
   ```bash
   # Clean APT cache
   apt clean

   # Remove old logs
   find /var/log -name "*.gz" -type f -mtime +30 -delete
   find /var/log -name "*.log.1" -type f -mtime +7 -delete

   # Clean old backups
   find /var/backups/youarecoder/database -name "*.sql.gz" -type f -mtime +30 -delete
   ```

2. **Identify large files:**
   ```bash
   du -sh /* | sort -h | tail -10
   du -sh /var/* | sort -h | tail -10
   du -sh /root/* | sort -h | tail -10
   ```

### Traffic Spike / DDoS

1. **Enable rate limiting (already configured):**
   ```bash
   # Check current rate limits in Flask
   grep -A 5 "RATELIMIT" /root/youarecoder/config.py
   ```

2. **Monitor connections:**
   ```bash
   # Active connections
   ss -s

   # Top IPs
   tail -1000 /var/log/traefik/access.log | awk '{print $1}' | sort | uniq -c | sort -rn | head -20
   ```

3. **Block malicious IP (if identified):**
   ```bash
   # Temporary block
   iptables -A INPUT -s MALICIOUS_IP -j DROP

   # Permanent block (add to /etc/iptables/rules.v4)
   ```

---

## Contact & Escalation

**System Owner:** [Your Name/Company]
**Emergency Contact:** [Phone Number]
**Support Email:** [support@youarecoder.com]

**External Services:**
- **Domain Registrar:** [Provider Name]
- **Hosting Provider:** Hetzner
- **SSL Provider:** Let's Encrypt (auto-renew)

---

## Appendix

### Useful Commands Reference
```bash
# Service management
systemctl start|stop|restart|status <service>
journalctl -u <service> -f

# Process management
ps aux | grep <process>
kill -9 <PID>

# Network
ss -tlnp
netstat -tulpn
curl -I <url>

# Disk
df -h
du -sh <path>
find <path> -size +100M

# Database
sudo -u postgres psql
\l  # List databases
\c <database>  # Connect
\dt  # List tables

# Git
git status
git pull
git log --oneline -10
```

### Configuration Files
| Component | Config Path |
|-----------|-------------|
| Flask App | `/root/youarecoder/config.py` |
| Environment | `/root/youarecoder/.env` |
| Traefik Static | `/etc/traefik/traefik.yml` |
| Traefik Dynamic | `/etc/traefik/dynamic/` |
| PostgreSQL | `/etc/postgresql/*/main/postgresql.conf` |
| Systemd Flask | `/etc/systemd/system/youarecoder.service` |
| Systemd Traefik | `/etc/systemd/system/traefik.service` |
| Logrotate Flask | `/etc/logrotate.d/youarecoder` |
| Logrotate Traefik | `/etc/logrotate.d/traefik` |
| Cron Jobs | `crontab -l` |

---

**End of Admin Playbook**
