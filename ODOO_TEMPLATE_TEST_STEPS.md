# Odoo 18.4 Template System - Test Steps

## Deployment Summary

✅ **Deployment Status**: Complete
✅ **Template ID**: 7
✅ **Template Name**: Odoo 18.4 Development
✅ **Service Status**: Running (4 workers)
✅ **Database Migration**: Completed (access_token, ssh_public_key fields added)

---

## Test Plan Overview

This test plan validates the complete Odoo 18.4 workspace provisioning system including:
- Token-based authentication
- SSH key generation and management
- PostgreSQL database provisioning
- Multi-folder workspace configuration
- VS Code launch.json setup
- Email notifications with SSH instructions

---

## Pre-Test Verification

### 1. Verify Template Exists
```bash
ssh root@37.27.21.167 'sudo -u postgres psql -d youarecoder -c "SELECT id, name, visibility, (config->>'\''ssh_required'\'')::boolean as ssh_required FROM workspace_templates WHERE id = 7;"'
```

**Expected Output**:
```
 id |         name          | visibility | ssh_required
----+-----------------------+------------+--------------
  7 | Odoo 18.4 Development | official   | t
```

### 2. Verify Service Health
```bash
ssh root@37.27.21.167 'systemctl status youarecoder --no-pager | head -10'
```

**Expected**: `Active: active (running)`

---

## Test Case 1: Create Odoo Workspace via Web UI

### Steps:
1. **Navigate to YouAreCoder**
   - URL: https://youarecoder.com
   - Login with test account

2. **Create New Workspace**
   - Click "Create Workspace" button
   - Fill in workspace details:
     - **Name**: `odoo-test-$(date +%s)`
     - **Template**: Select "Odoo 18.4 Development"
     - **Disk Quota**: 20 GB (recommended for Odoo)
   - Click "Create Workspace"

3. **Monitor Provisioning**
   - Watch workspace status change: `pending` → `provisioning` → `running`
   - Estimated time: 5-10 minutes (includes git clones and package installation)

### Expected Results:
- ✅ Workspace status becomes "running"
- ✅ Access URL is displayed with token parameter
- ✅ SSH setup modal appears (if SSH key generated)
- ✅ Email notification sent to user

### Validation Queries:
```bash
# Check workspace created
ssh root@37.27.21.167 'sudo -u postgres psql -d youarecoder -c "SELECT id, name, subdomain, status, access_token IS NOT NULL as has_token, ssh_public_key IS NOT NULL as has_ssh FROM workspaces ORDER BY created_at DESC LIMIT 1;"'

# Expected: has_token = t, has_ssh = t, status = running
```

---

## Test Case 2: Verify Token-Based Authentication

### Steps:
1. **Get Workspace Access URL**
   ```bash
   ssh root@37.27.21.167 'sudo -u postgres psql -d youarecoder -c "SELECT subdomain, access_token FROM workspaces WHERE template_id = 7 ORDER BY created_at DESC LIMIT 1;"'
   ```

2. **Access Workspace**
   - URL format: `https://{subdomain}.youarecoder.com/?token={access_token}`
   - Example: `https://ws-abc123.youarecoder.com/?token=xYz123...`

3. **Test Direct Access (Without Token)**
   - Try accessing without `?token=` parameter
   - Should be denied (code-server auth required)

### Expected Results:
- ✅ With token: Immediate access to VS Code (no password prompt)
- ✅ Without token: Access denied or password prompt
- ✅ Token is URL-safe (no special characters that break URLs)

---

## Test Case 3: SSH Key Management

### Steps:
1. **Verify SSH Key Generation**
   ```bash
   # Get workspace Linux username
   ssh root@37.27.21.167 'sudo -u postgres psql -d youarecoder -c "SELECT linux_username FROM workspaces WHERE template_id = 7 ORDER BY created_at DESC LIMIT 1;"'

   # Check SSH key exists
   ssh root@37.27.21.167 'ls -la /home/{linux_username}/.ssh/'
   ```

2. **Verify Public Key Stored**
   ```bash
   ssh root@37.27.21.167 'sudo -u postgres psql -d youarecoder -c "SELECT substring(ssh_public_key, 1, 50) || '\''...'\'' as key_preview FROM workspaces WHERE template_id = 7 ORDER BY created_at DESC LIMIT 1;"'
   ```

3. **Test SSH Setup Modal** (via Web UI)
   - Click "SSH Setup" button in workspace details
   - Verify modal displays:
     - SSH public key
     - Copy button
     - GitHub instructions
     - Verify button

4. **Add SSH Key to GitHub** (Manual Step)
   - Go to https://github.com/settings/ssh/new
   - Paste the SSH public key
   - Title: `{subdomain} - YouAreCoder`
   - Click "Add SSH key"

5. **Verify SSH Connection**
   - Click "Verify SSH" button in modal
   - Should test `ssh -T git@github.com`

### Expected Results:
- ✅ SSH key pair generated (ED25519 algorithm)
- ✅ Public key stored in database
- ✅ known_hosts includes github.com
- ✅ Modal displays key correctly
- ✅ Copy button works
- ✅ Verification succeeds after adding key to GitHub

---

## Test Case 4: PostgreSQL Database Provisioning

### Steps:
1. **Access Workspace Terminal**
   - Use token-based URL
   - Open Terminal in VS Code

2. **Verify PostgreSQL User**
   ```bash
   psql -l
   # Should list databases without password prompt
   ```

3. **Verify Odoo Database**
   ```bash
   psql -d odoo_dev -c "SELECT version();"
   ```

4. **Check User Privileges**
   ```bash
   psql -c "\du" | grep $(whoami)
   ```

### Expected Results:
- ✅ PostgreSQL user exists (matches Linux username)
- ✅ Database `odoo_dev` exists
- ✅ User has superuser privileges
- ✅ No password required (peer authentication)

---

## Test Case 5: Multi-Folder Workspace Verification

### Steps:
1. **Check Workspace File**
   ```bash
   cat ~/.workspace.code-workspace | jq '.folders'
   ```

2. **Verify Folders Exist**
   ```bash
   ls -la ~/ | grep odoo
   ```

3. **Verify Repositories Cloned**
   ```bash
   # Community (public)
   ls -la ~/odoo-community/.git

   # Enterprise (private - requires SSH key)
   ls -la ~/odoo-enterprise/.git

   # Dev tools
   ls -la ~/odoo-dev-tools/.git

   # Custom modules directory
   ls -la ~/odoo-customs/
   ```

4. **Check VS Code Opened Workspace**
   - Workspace should auto-open on first VS Code launch
   - Verify 4 folders in explorer:
     - Odoo Community
     - Odoo Enterprise
     - Custom Modules
     - Development Tools

### Expected Results:
- ✅ [.workspace.code-workspace](.workspace.code-workspace:1) file exists
- ✅ All 4 folders defined
- ✅ 3 repositories cloned successfully
- ✅ odoo-customs directory created
- ✅ VS Code shows multi-folder workspace

---

## Test Case 6: VS Code Launch Configuration

### Steps:
1. **Check launch.json Exists**
   ```bash
   cat ~/odoo-dev-tools/.vscode/launch.json | jq '.configurations[].name'
   ```

2. **Verify Python Debugger Extension**
   ```bash
   code --list-extensions | grep debugpy
   ```

3. **Test Run Configuration**
   - Open VS Code Run/Debug view (Ctrl+Shift+D)
   - Select "Odoo: Run Development Server"
   - Press F5 or click "Start Debugging"

4. **Verify Odoo Starts**
   - Check terminal output for Odoo server startup
   - Wait for "HTTP service (werkzeug) running on"
   - Default port: 8069

### Expected Results:
- ✅ [launch.json](launch.json:1) exists in .vscode directory
- ✅ Two configurations available:
  - "Odoo: Run Development Server"
  - "Odoo: Update Module"
- ✅ Python debugger extension installed
- ✅ Odoo starts successfully with `-i base` parameter
- ✅ Database initialized with base modules

---

## Test Case 7: Python Virtual Environment

### Steps:
1. **Verify Venv Exists**
   ```bash
   ls -la ~/odoo-dev-tools/venv/bin/python
   ```

2. **Check Installed Packages**
   ```bash
   source ~/odoo-dev-tools/venv/bin/activate
   pip list | grep -E '(odoo|psycopg2|lxml|pillow)'
   ```

3. **Verify Odoo Requirements**
   ```bash
   pip check
   # Should show no dependency conflicts
   ```

### Expected Results:
- ✅ Virtual environment created in [~/odoo-dev-tools/venv](~/odoo-dev-tools/venv:1)
- ✅ Odoo requirements.txt installed
- ✅ Key packages present:
  - psycopg2 (PostgreSQL adapter)
  - lxml (XML processing)
  - Pillow (image processing)
  - Werkzeug (WSGI server)
- ✅ No dependency conflicts

---

## Test Case 8: Email Notification Verification

### Steps:
1. **Check Email Sent**
   ```bash
   ssh root@37.27.21.167 'tail -50 /var/log/youarecoder/error.log | grep "Email sent"'
   ```

2. **Verify Email Content** (Manual - Check user's email inbox)
   - Subject: "Your Workspace 'odoo-test-xxx' is Ready! 🚀"
   - Workspace details section
   - SSH key section (conditional)
   - Access URL with token
   - Setup instructions

3. **Check SSH Key in Email**
   - Verify SSH public key displayed
   - Verify GitHub setup instructions (5 steps)
   - Verify warning about requirement

### Expected Results:
- ✅ Email sent successfully
- ✅ Contains workspace access URL with token
- ✅ Contains SSH public key (if generated)
- ✅ Contains setup instructions
- ✅ HTML and plain text versions sent

---

## Test Case 9: Workspace Configuration File (odoo.conf)

### Steps:
1. **Verify Config File**
   ```bash
   cat ~/odoo-dev-tools/odoo.conf
   ```

2. **Check Key Settings**
   ```bash
   grep -E "(addons_path|db_name|db_user)" ~/odoo-dev-tools/odoo.conf
   ```

3. **Test Config with Odoo**
   ```bash
   cd ~/odoo-dev-tools
   source venv/bin/activate
   python odoo-run.py --config=odoo.conf -d odoo_dev --stop-after-init
   ```

### Expected Results:
- ✅ [odoo.conf](odoo.conf:1) exists in odoo-dev-tools
- ✅ Key settings configured:
  - `addons_path` includes community, enterprise, customs
  - `db_name = odoo_dev`
  - `db_user = {linux_username}`
  - `http_port = 8069`
- ✅ Odoo accepts configuration without errors

---

## Test Case 10: End-to-End Development Workflow

### Complete Workflow Test:
1. **Create Custom Module**
   ```bash
   cd ~/odoo-customs
   mkdir -p my_test_module
   cat > my_test_module/__manifest__.py << 'EOF'
   {
       'name': 'Test Module',
       'version': '18.0.1.0.0',
       'depends': ['base'],
       'data': [],
       'installable': True,
   }
   EOF
   ```

2. **Start Odoo with Debugger**
   - Open VS Code
   - Select "Odoo: Update Module" configuration
   - Enter module name: `my_test_module`
   - Press F5
   - Set breakpoint in module code

3. **Access Odoo Web Interface**
   - Open browser: `http://localhost:8069`
   - Login (default: admin/admin if first init)
   - Go to Apps
   - Search for "Test Module"
   - Install module

4. **Verify Debugger Hits Breakpoint**
   - Module installation should trigger breakpoint
   - Inspect variables
   - Step through code

### Expected Results:
- ✅ Custom module created successfully
- ✅ VS Code debugger attaches to Odoo process
- ✅ Breakpoints work correctly
- ✅ Odoo web interface accessible
- ✅ Module installation succeeds
- ✅ Complete development workflow functional

---

## Test Case 11: SSH Private Repository Clone (Odoo Enterprise)

### Prerequisites:
- SSH key added to GitHub account
- Access granted to odoo/enterprise repository

### Steps:
1. **Verify Enterprise Repo Cloned**
   ```bash
   cd ~/odoo-enterprise
   git remote -v
   git log -1 --oneline
   ```

2. **Test Git Pull**
   ```bash
   git pull origin 18.0
   ```

3. **Verify No SSH Prompts**
   - Should complete without password/passphrase prompts
   - Should use SSH key authentication automatically

### Expected Results:
- ✅ Enterprise repository cloned successfully
- ✅ Uses SSH URL: `git@github.com:odoo/enterprise.git`
- ✅ Branch 18.0 checked out
- ✅ Git pull works without prompts
- ✅ known_hosts includes github.com (no fingerprint prompt)

---

## Troubleshooting Guide

### Issue: Workspace Stuck in "Provisioning"
**Diagnosis**:
```bash
ssh root@37.27.21.167 'tail -100 /var/log/youarecoder/error.log | grep -A 10 "workspace_id"'
```

**Common Causes**:
- Package installation timeout
- Git clone failure (SSH key not added)
- Disk space exhaustion
- PostgreSQL service down

### Issue: Token Authentication Not Working
**Diagnosis**:
```bash
# Check token exists
ssh root@37.27.21.167 'sudo -u postgres psql -d youarecoder -c "SELECT id, subdomain, access_token FROM workspaces WHERE template_id = 7 ORDER BY created_at DESC LIMIT 1;"'

# Check code-server service
ssh root@37.27.21.167 'systemctl status code-server@{linux_username}'
```

**Fix**:
```bash
# Restart code-server service
ssh root@37.27.21.167 'systemctl restart code-server@{linux_username}'
```

### Issue: SSH Private Repo Clone Fails
**Diagnosis**:
```bash
# Check SSH key exists
ssh root@37.27.21.167 'ls -la /home/{linux_username}/.ssh/'

# Test GitHub connection
ssh root@37.27.21.167 'sudo -u {linux_username} ssh -T git@github.com'
```

**Fix**:
1. Verify SSH key added to GitHub
2. Check known_hosts: `cat ~/.ssh/known_hosts | grep github`
3. Manually test: `git clone git@github.com:odoo/enterprise.git test-clone`

### Issue: PostgreSQL Connection Refused
**Diagnosis**:
```bash
ssh root@37.27.21.167 'systemctl status postgresql'
ssh root@37.27.21.167 'sudo -u postgres psql -c "\du"'
```

**Fix**:
```bash
ssh root@37.27.21.167 'systemctl restart postgresql'
```

### Issue: VS Code Launch Config Not Working
**Diagnosis**:
```bash
# Check launch.json exists and is valid JSON
cat ~/odoo-dev-tools/.vscode/launch.json | jq '.'

# Check Python extension
code --list-extensions | grep python
```

**Fix**:
1. Reinstall Python extension: `code --install-extension ms-python.python`
2. Verify venv Python: `which python` (should be in odoo-dev-tools/venv)
3. Reload VS Code window

---

## Performance Benchmarks

### Expected Provisioning Times:
- **User Creation**: 10-15 seconds
- **Package Installation**: 2-3 minutes (25 packages)
- **Git Repository Clones**:
  - odoo-community: 1-2 minutes (~500MB)
  - odoo-enterprise: 30-60 seconds (~100MB)
  - odoo-dev-tools: 10-20 seconds
- **Python Venv Setup**: 1-2 minutes
- **PostgreSQL Setup**: 5-10 seconds
- **Total Provisioning**: 5-10 minutes

### Resource Usage (Per Workspace):
- **Disk Space**: 2-3 GB (after full setup with Odoo)
- **RAM**: 512 MB - 2 GB (depending on Odoo workload)
- **CPU**: Low (idle), High (during Odoo startup/module install)

---

## Success Criteria

### Deployment Success:
- [x] Template seeded in database (ID: 7)
- [x] Database migration completed
- [x] Service running with 4 workers
- [x] No errors in application logs

### Functional Success:
- [ ] Workspace created with Odoo template
- [ ] Token-based authentication works
- [ ] SSH key generated and stored
- [ ] All 3 repositories cloned
- [ ] PostgreSQL database provisioned
- [ ] VS Code workspace opened with 4 folders
- [ ] Launch configurations working
- [ ] Python venv functional
- [ ] Email notification sent
- [ ] Odoo starts successfully with `-i base`

### Quality Success:
- [ ] No provisioning errors
- [ ] All components verified
- [ ] Documentation complete
- [ ] User can develop Odoo modules

---

## Next Steps After Testing

1. **Test with Real User**
   - Create workspace through web UI
   - Verify all features from user perspective
   - Collect feedback

2. **Monitor Production Logs**
   ```bash
   ssh root@37.27.21.167 'tail -f /var/log/youarecoder/error.log'
   ```

3. **Verify Email Delivery**
   - Check Mailjet dashboard
   - Verify email not in spam

4. **Performance Monitoring**
   - Track provisioning times
   - Monitor disk usage
   - Check memory consumption

5. **Documentation Updates**
   - User guide for Odoo template
   - SSH key setup tutorial
   - Troubleshooting FAQ

---

## Test Results Summary

**Date**: 2025-11-01
**Tester**: ________________
**Environment**: Production (youarecoder.com)

| Test Case | Status | Notes |
|-----------|--------|-------|
| 1. Create Workspace | ⏳ Pending | |
| 2. Token Auth | ⏳ Pending | |
| 3. SSH Key Management | ⏳ Pending | |
| 4. PostgreSQL | ⏳ Pending | |
| 5. Multi-Folder Workspace | ⏳ Pending | |
| 6. Launch Configuration | ⏳ Pending | |
| 7. Python Venv | ⏳ Pending | |
| 8. Email Notification | ⏳ Pending | |
| 9. Odoo Config | ⏳ Pending | |
| 10. E2E Workflow | ⏳ Pending | |
| 11. Private Repo Clone | ⏳ Pending | |

**Overall Status**: ⏳ Testing in Progress

---

## Contact & Support

For issues or questions:
- **Application Logs**: `/var/log/youarecoder/error.log`
- **Service Status**: `systemctl status youarecoder`
- **Database**: `sudo -u postgres psql -d youarecoder`
- **Support Email**: support@youarecoder.com
