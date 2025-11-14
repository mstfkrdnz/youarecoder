# YouAreCoder Deployment Workflow

## ⚠️ CRITICAL: Always Check First!

Before ANY code changes to YouAreCoder project:

```bash
ssh root@37.27.21.167 'youarecoder-check'
```

## Production Directory

**CORRECT:** `/root/youarecoder/`  
**WRONG:** `/var/www/youarecoder/` (exists but unused!)

## Standard Workflow

### 1. Pre-Check
```bash
# Verify working directory
cat /etc/systemd/system/youarecoder.service | grep WorkingDirectory
# Should show: /root/youarecoder
```

### 2. Make Changes
```bash
# Edit files in correct directory
vim /root/youarecoder/app/templates/...
vim /root/youarecoder/app/routes/...
```

### 3. Deploy
```bash
# Force restart to ensure clean state
ssh root@37.27.21.167 'pkill -9 gunicorn && sudo systemctl start youarecoder'

# Verify processes started recently
ssh root@37.27.21.167 'ps aux | grep gunicorn | grep -v grep | head -2'
# Check start time should be current date/time
```

### 4. Verify
```bash
# Check environment
ssh root@37.27.21.167 'youarecoder-check'

# Look for recent file modifications
# Look for current process start times
```

## Key Locations

- **Templates:** `/root/youarecoder/app/templates/`
- **Routes:** `/root/youarecoder/app/routes/`
- **Models:** `/root/youarecoder/app/models/`
- **Service:** `/etc/systemd/system/youarecoder.service`
- **Logs:** `/var/log/youarecoder/error.log`

## Quick Commands

```bash
# Environment check
youarecoder-check

# Restart service
sudo systemctl restart youarecoder

# Force restart (recommended)
pkill -9 gunicorn && sudo systemctl start youarecoder

# View logs
tail -f /var/log/youarecoder/error.log

# Check process start times
ps aux | grep gunicorn | grep -v grep
```

## Historical Issue (2025-11-14)

**Problem:** Edited `/var/www/youarecoder/` but changes didn't apply  
**Root Cause:** Wrong directory - app runs from `/root/youarecoder/`  
**Time Lost:** 2 hours debugging "cache" issues  
**Lesson:** Always run `youarecoder-check` first!

## Detection Signs

If changes don't apply:
1. Check `ps aux | grep gunicorn` - are start times old?
2. Run `youarecoder-check` - shows working directory
3. Verify you edited files in `/root/youarecoder/` not `/var/www/`
