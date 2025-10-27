# YouAreCoder Troubleshooting Guide

Quick solutions to common problems.

---

## Table of Contents

1. [Login Issues](#login-issues)
2. [Workspace Problems](#workspace-problems)
3. [Performance Issues](#performance-issues)
4. [Connection Problems](#connection-problems)
5. [Browser Issues](#browser-issues)

---

## Login Issues

### Cannot Login / "Invalid Credentials"

**Possible Causes:**
- Incorrect username/password
- Account locked (too many failed attempts)
- Caps Lock enabled
- Browser autofill error

**Solutions:**
1. **Verify credentials:**
   - Username is case-sensitive
   - Check Caps Lock is OFF
   - Clear browser autofill, type manually

2. **Account locked:**
   - Wait 30 minutes for automatic unlock
   - Contact support for immediate unlock

3. **Reset password:**
   - Contact support@youarecoder.com
   - Provide registered email address

### "Session Expired" Message

**Solution:**
```
1. Clear browser cookies for youarecoder.com
2. Close all youarecoder.com tabs
3. Reopen browser
4. Login again
```

### Redirects to Wrong Subdomain

**Cause:** Accessing wrong company URL

**Solution:**
```
✅ Correct: https://yourcompany.youarecoder.com
❌ Wrong: https://youarecoder.com
```

Check your company subdomain in registration email.

---

## Workspace Problems

### Workspace Won't Open

**Symptom:** Clicking "Open" does nothing or shows error

**Solutions:**

**1. Check Workspace Status:**
```
If status is "Stopped" → Click "Start" first
If status is "Error" → Click "Restart"
If status is "Provisioning" → Wait 1-2 minutes
```

**2. Clear Browser Cache:**
```
Chrome/Edge: Ctrl+Shift+Delete → Clear cache
Firefox: Ctrl+Shift+Delete → Clear cache
Safari: Cmd+Option+E → Empty caches
```

**3. Try Incognito/Private Mode:**
- Eliminates browser extension conflicts
- Tests if issue is browser-related

**4. Check Direct URL:**
```
Format: https://workspace-company.youarecoder.com
Example: https://myproject-acmecorp.youarecoder.com
```

### "Password Required" on Workspace

**This is Normal!** Each workspace has its own password for security.

**Find Password:**
1. Go to dashboard
2. Find workspace card
3. Password shown below workspace name
4. Copy and paste into prompt

**Lost Password?**
- Contact support for password reset

### Workspace is Slow

**Quick Fixes:**
1. **Restart Workspace:**
   - Dashboard → Find workspace → Click "Restart"
   - Wait 30 seconds, then "Open"

2. **Close Unused Tabs:**
   - Close files you're not editing
   - Close unused terminal tabs

3. **Stop Heavy Processes:**
   ```bash
   # Check running processes
   top

   # Kill specific process
   kill -9 <PID>
   ```

4. **Clear Workspace Cache:**
   ```bash
   # Node modules
   rm -rf node_modules && npm install

   # Python cache
   find . -type d -name "__pycache__" -exec rm -r {} +
   ```

### Files Disappeared

**Don't Panic!** Files are rarely lost.

**Check:**
1. **Wrong Directory:**
   ```bash
   # Find your files
   find ~ -name "filename" -type f

   # List all directories
   ls -la ~
   ```

2. **Hidden Files:**
   ```bash
   # Show hidden files in terminal
   ls -la

   # In VS Code: View → Show Hidden Files
   ```

3. **Git Uncommitted Changes:**
   ```bash
   git status
   git stash list
   ```

**Recovery:**
```bash
# Check backups (daily automated)
# Contact support with:
# - Workspace name
# - Approximate file location
# - Last known file content
```

### Can't Install Packages

**NPM Issues:**
```bash
# Clear cache
npm cache clean --force

# Delete lock file
rm package-lock.json

# Reinstall
npm install
```

**Python Issues:**
```bash
# Upgrade pip
pip install --upgrade pip

# Install with verbose
pip install <package> -v

# Check permissions
ls -l /home/yac_*
```

**System Package Issues:**
```bash
# Not allowed: sudo apt install (no sudo access)
# Use: User-space alternatives
# - npm/yarn for Node packages
# - pip for Python packages
# - Download binaries manually
```

---

## Performance Issues

### Slow Loading

**Network Check:**
```
1. Test internet speed: speedtest.net
2. Minimum required: 5 Mbps
3. Recommended: 10+ Mbps
```

**Browser Check:**
```
1. Close other tabs (especially video)
2. Disable unnecessary extensions
3. Clear browser cache
4. Try different browser
```

**Workspace Check:**
```
1. Restart workspace
2. Check resource usage:
   top
   df -h
3. Close heavy processes
```

### High Memory Usage

**Identify Culprit:**
```bash
# Sort by memory
top
# Press Shift+M to sort by memory

# Or use:
ps aux --sort=-%mem | head -20
```

**Common Causes:**
- Node.js dev servers
- Multiple Python processes
- Large file operations

**Solutions:**
```bash
# Kill specific process
kill -9 <PID>

# Restart workspace (nuclear option)
Dashboard → Restart
```

### Disk Space Full

**Check Usage:**
```bash
df -h
du -sh ~/* | sort -h
```

**Clean Up:**
```bash
# Node modules (safe to delete, reinstall)
find . -name "node_modules" -type d -prune -exec rm -rf '{}' +

# Python cache
find . -type d -name "__pycache__" -exec rm -r {} +

# Build artifacts
rm -rf dist/ build/ *.egg-info

# Old logs
rm *.log

# Temporary files
rm -rf /tmp/*
```

---

## Connection Problems

### "Connection Lost" Error

**Immediate Actions:**
1. Check internet connection
2. Try refreshing page (F5)
3. Reopen workspace

**If Persists:**
1. Check system status
2. Try different network
3. Contact support if widespread

### Terminal Won't Connect

**Solutions:**
```
1. Close all terminal tabs
2. Reload VS Code (Ctrl+R)
3. Open new terminal
4. If fails, restart workspace
```

### Git Push/Pull Fails

**SSH Key Issues:**
```bash
# Generate new SSH key
ssh-keygen -t ed25519 -C "your-email@example.com"

# Add to GitHub/GitLab
cat ~/.ssh/id_ed25519.pub
# Copy output, add to Git provider
```

**HTTPS Authentication:**
```bash
# Use personal access token instead of password
git clone https://username:TOKEN@github.com/user/repo.git

# Or configure credential helper
git config --global credential.helper store
```

---

## Browser Issues

### Blank Screen

**Fixes:**
1. Hard refresh: Ctrl+Shift+R (Cmd+Shift+R Mac)
2. Clear browser cache
3. Disable browser extensions
4. Try incognito mode
5. Try different browser

### UI Elements Missing

**Cause:** Zoom level or screen resolution

**Solution:**
```
1. Reset zoom: Ctrl+0 (Cmd+0 Mac)
2. Adjust VS Code zoom:
   - View → Appearance → Zoom In/Out
3. Check screen resolution (minimum 1024x768)
```

### Keyboard Shortcuts Don't Work

**Cause:** Browser capturing shortcuts

**Solution:**
1. **Chrome/Edge:**
   - Settings → Advanced → System
   - Disable "Continue running apps..."

2. **Firefox:**
   - about:config
   - browser.ctrlTab.previews → false

3. **Use Command Palette:**
   - Ctrl+Shift+P (Cmd+Shift+P Mac)
   - Type command name

### Copy/Paste Not Working

**Solution:**
```
1. Use VS Code shortcuts:
   - Copy: Ctrl+C (Cmd+C Mac)
   - Paste: Ctrl+V (Cmd+V Mac)

2. Or right-click menu:
   - Right-click → Copy/Paste

3. Browser permission:
   - Allow clipboard access when prompted
```

---

## Error Messages

### "Workspace Limit Reached"

**Meaning:** Your plan's workspace limit reached

**Solutions:**
1. Delete unused workspaces
2. Upgrade plan (Dashboard → Settings → Upgrade)

### "Insufficient Storage"

**Meaning:** Disk quota exceeded

**Check Usage:**
- Dashboard shows storage used
- Plan limits: Starter 10GB, Team 50GB, Enterprise 250GB

**Solutions:**
1. Clean up files (see [Disk Space Full](#disk-space-full))
2. Delete large files:
   ```bash
   find ~ -type f -size +100M -exec ls -lh {} \;
   ```
3. Upgrade plan for more storage

### "Service Unavailable"

**Meaning:** Temporary server issue

**Actions:**
1. Wait 2-3 minutes
2. Try again
3. Check https://status.youarecoder.com (coming soon)
4. Contact support if persists >15 minutes

---

## Getting Help

### Before Contacting Support

1. **Try basic troubleshooting** (restart workspace, clear cache)
2. **Check this guide** for your specific issue
3. **Note error messages** (screenshot if possible)
4. **Test in incognito** mode

### Contacting Support

**Email:** support@youarecoder.com

**Include:**
- Your email address
- Company subdomain
- Workspace name (if applicable)
- Problem description
- Error messages
- Steps to reproduce
- Browser & OS version
- Screenshots (optional)

**Response Time:** Within 24 hours (business days)

---

## Quick Diagnostics

Run these commands to gather diagnostic info:

```bash
# System info
uname -a
df -h
free -h

# Workspace info
whoami
pwd
ls -la ~

# Network
ping -c 4 google.com
curl -I https://youarecoder.com

# Processes
ps aux | head -20
top -bn1 | head -20
```

Copy output when contacting support.

---

**Still Having Issues?**

Contact: support@youarecoder.com

We're here to help! 🚀
