# YouAreCoder Project Instructions for Claude

## 🚨 DEPLOYMENT WORKFLOW - READ THIS FIRST!

Before making ANY changes to YouAreCoder:

### 1. ⚠️ CRITICAL: Verify Correct Directory

**Production app runs from:** `/root/youarecoder/` (on server 37.27.21.167)
**DO NOT edit:** `/var/www/youarecoder/` - This directory is UNUSED!

### 2. Pre-Change Checklist

```bash
# Run environment check
ssh root@37.27.21.167 'youarecoder-check'

# Verify service configuration
ssh root@37.27.21.167 'cat /etc/systemd/system/youarecoder.service | grep WorkingDirectory'
# Expected: WorkingDirectory=/root/youarecoder
```

### 3. Standard Deployment Flow

```bash
# 1. Make changes in: /root/youarecoder/
# 2. Force restart:
ssh root@37.27.21.167 'pkill -9 gunicorn && sudo systemctl start youarecoder'

# 3. Verify restart:
ssh root@37.27.21.167 'ps aux | grep gunicorn | grep -v grep | head -2'
# ✓ Check start times are RECENT (today's date/time)

# 4. Final check:
ssh root@37.27.21.167 'youarecoder-check'
```

### 4. Detection: Changes Not Applying?

If changes don't show up in browser:

1. **Check process start times:**
   ```bash
   ps aux | grep gunicorn | grep -v grep
   ```
   If start times are old (not today), processes didn't restart!

2. **Check which directory you edited:**
   - ✓ Correct: `/root/youarecoder/`
   - ✗ Wrong: `/var/www/youarecoder/`

3. **Run diagnostic:**
   ```bash
   ssh root@37.27.21.167 'youarecoder-check'
   ```

### 5. Project Structure

**Server:** 37.27.21.167
**App Directory:** `/root/youarecoder/`
**Service File:** `/etc/systemd/system/youarecoder.service`
**Logs:** `/var/log/youarecoder/error.log`, `/var/log/youarecoder/access.log`

Key directories:
- Templates: `/root/youarecoder/app/templates/`
- Routes: `/root/youarecoder/app/routes/`
- Models: `/root/youarecoder/app/models/`

### 6. Historical Context

**2025-11-14 Incident:**
- Issue: JavaScript duplicate `const statusMessage` error
- Mistake: Spent 2 hours editing `/var/www/youarecoder/` (wrong directory!)
- Changes never applied because app runs from `/root/youarecoder/`
- Detection: `ps aux` showed Nov 13 start times = never restarted
- Lesson: **Always run `youarecoder-check` first!**

## Project Context

- **Tech Stack:** Flask, Gunicorn, PostgreSQL, Tailwind CSS
- **Authentication:** Flask-Login with session management
- **Workspace System:** Container-based isolated development environments
- **Payment:** PayTR integration for Turkish market
- **Provisioning:** Automated workspace setup with SSH verification workflow

## Common Tasks

### Restart Application
```bash
# Method 1: Standard restart
sudo systemctl restart youarecoder

# Method 2: Force restart (recommended for template changes)
pkill -9 gunicorn && sudo systemctl start youarecoder
```

### View Logs
```bash
# Error logs
tail -f /var/log/youarecoder/error.log

# Access logs
tail -f /var/log/youarecoder/access.log
```

### Database Access
```bash
# Connect to database
sudo -u postgres psql -d youarecoder

# Common queries
SELECT id, email, role FROM users;
SELECT id, name, provisioning_state FROM workspaces;
```

## Important Notes

- **Always use absolute paths** when SSHing to edit files
- **Force kill gunicorn** before restart to ensure clean state
- **Verify process start times** after every restart
- **Run `youarecoder-check`** before and after changes
- **Never commit** database credentials or secrets
