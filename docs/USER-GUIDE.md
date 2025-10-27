# YouAreCoder User Guide

**Welcome to YouAreCoder!** This guide will help you get started with your cloud development workspaces.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Creating Your First Workspace](#creating-your-first-workspace)
3. [Accessing Your Workspace](#accessing-your-workspace)
4. [Managing Workspaces](#managing-workspaces)
5. [Tips & Best Practices](#tips--best-practices)
6. [FAQ](#faq)
7. [Support](#support)

---

## Getting Started

### What is YouAreCoder?

YouAreCoder provides cloud-based development workspaces powered by VS Code. Access your full development environment from any device with a web browser.

**Key Features:**
- ✅ Full VS Code experience in your browser
- ✅ Pre-configured development environment
- ✅ Access from anywhere
- ✅ Automatic backups
- ✅ SSL-secured connections
- ✅ Isolated workspaces per project

### System Requirements

**Minimum:**
- Modern web browser (Chrome, Firefox, Safari, Edge)
- Stable internet connection (5 Mbps+)
- JavaScript enabled

**Recommended:**
- Chrome or Edge (best performance)
- 10 Mbps+ internet connection
- Screen resolution 1920x1080 or higher

---

## Creating Your First Workspace

### Step 1: Register Your Company

1. Visit [https://youarecoder.com](https://youarecoder.com)
2. Click **"Start Free Trial"**
3. Fill in registration form:
   - Company Name
   - Subdomain (e.g., `mycompany` → `mycompany.youarecoder.com`)
   - Your Name
   - Username
   - Email
   - Password (min 8 characters, must include uppercase, lowercase, digit, special character)
4. Click **"Create Account"**
5. You'll be redirected to login page

### Step 2: Login

1. Visit `https://yoursubdomain.youarecoder.com`
2. Enter your username/email and password
3. Click **"Sign in"**
4. You'll see your dashboard

### Step 3: Create Workspace

1. Click **"New Workspace"** button on dashboard
2. Enter workspace name (lowercase, hyphens allowed)
   - Good: `project-alpha`, `backend-api`
   - Bad: `Project Alpha`, `backend_api`
3. Click **"Create Workspace"**
4. Wait 30-60 seconds for provisioning
5. Workspace card will appear with **"Open"** button

---

## Accessing Your Workspace

### Opening Your Workspace

**Method 1: Dashboard**
1. Log in to your company dashboard
2. Find your workspace card
3. Click **"Open"** button

**Method 2: Direct URL**
- Visit: `https://workspacename-yoursubdomain.youarecoder.com`
- Example: `https://project-alpha-mycompany.youarecoder.com`

### First-Time Setup

When you open your workspace for the first time:

1. **Password Prompt:** Enter the workspace password (shown on workspace card)
2. **VS Code Opens:** Full VS Code interface loads in browser
3. **File Explorer:** Left sidebar shows your workspace directory
4. **Terminal:** Access terminal via Menu → Terminal → New Terminal

---

## Managing Workspaces

### Dashboard Overview

Your dashboard shows:
- **Statistics:** Total workspaces, active workspaces, storage used
- **Workspace Cards:** All your workspaces with status
- **Quick Actions:** Create workspace, view settings

### Workspace Controls

Each workspace card has:
- **Name & Subdomain:** Click to copy URL
- **Status:** Active (green), Stopped (red), Provisioning (yellow)
- **Actions:**
  - **Open:** Launch VS Code
  - **Restart:** Restart workspace service
  - **Stop:** Temporarily stop workspace
  - **Start:** Start stopped workspace

### Workspace Status

| Status | Meaning | Action |
|--------|---------|--------|
| **Active** 🟢 | Running and accessible | Click "Open" to access |
| **Stopped** 🔴 | Not running, saves resources | Click "Start" to activate |
| **Provisioning** 🟡 | Being created | Wait 30-60 seconds |
| **Error** ⚠️ | Issue detected | Contact support |

---

## Tips & Best Practices

### Development Workflow

**1. Use Terminal Effectively:**
```bash
# Install packages
npm install <package>
pip install <package>

# Run development server
npm run dev
python manage.py runserver

# Git operations
git clone <repo-url>
git add .
git commit -m "message"
git push
```

**2. Install Extensions:**
- Click Extensions icon in sidebar
- Search for extensions (ESLint, Prettier, Python, etc.)
- Click "Install"

**3. Configure Settings:**
- File → Preferences → Settings
- Customize theme, font size, keybindings

### File Management

**Upload Files:**
1. Right-click in File Explorer
2. Select "Upload..."
3. Choose files from your computer

**Download Files:**
1. Right-click file in File Explorer
2. Select "Download"

**Create Files/Folders:**
- Right-click → New File / New Folder
- Or use terminal: `touch file.txt`, `mkdir folder`

### Performance Tips

- **Close Unused Tabs:** Free up memory
- **Use Search Wisely:** Exclude `node_modules` from search
- **Restart When Needed:** If workspace feels slow, restart it
- **Don't Run Heavy Tasks:** Workspaces have resource limits

### Security

- **Never Share Password:** Each workspace has unique password
- **Log Out:** When using shared computers
- **Use Strong Passwords:** For your account
- **Enable 2FA:** (Coming soon)

---

## FAQ

**Q: How much storage do I have?**
A: Storage depends on your plan (10GB Starter, 50GB Team, 250GB Enterprise)

**Q: Can I access from mobile?**
A: Yes, but desktop browser recommended for best experience

**Q: Is my code backed up?**
A: Yes, automated daily backups. Push to Git for additional safety

**Q: Can multiple people use one workspace?**
A: One user per workspace. Create multiple workspaces for team collaboration

**Q: What languages are supported?**
A: All languages supported by VS Code (Python, JavaScript, Go, Rust, etc.)

**Q: Can I install custom tools?**
A: Yes, install via terminal (npm, pip, apt, etc.)

**Q: Workspace won't start?**
A: Try "Restart" button. If issue persists, contact support

**Q: How do I upgrade my plan?**
A: Click "Upgrade" in dashboard settings

**Q: Can I change workspace name?**
A: Workspace names are immutable. Create new workspace if needed

**Q: Lost workspace password?**
A: Contact support for password reset

---

## Support

### Getting Help

**Documentation:**
- User Guide: [https://docs.youarecoder.com/user-guide](https://docs.youarecoder.com/user-guide)
- Troubleshooting: [https://docs.youarecoder.com/troubleshooting](https://docs.youarecoder.com/troubleshooting)

**Contact:**
- Email: support@youarecoder.com
- Response Time: Within 24 hours

**When Contacting Support:**
1. Describe the issue clearly
2. Include workspace name/subdomain
3. Mention error messages (if any)
4. Attach screenshots (optional)

---

## Quick Reference

### Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Command Palette | Ctrl+Shift+P (Cmd+Shift+P Mac) |
| Quick Open File | Ctrl+P (Cmd+P Mac) |
| New Terminal | Ctrl+Shift+` (Cmd+Shift+` Mac) |
| Find | Ctrl+F (Cmd+F Mac) |
| Replace | Ctrl+H (Cmd+H Mac) |
| Save | Ctrl+S (Cmd+S Mac) |
| Toggle Sidebar | Ctrl+B (Cmd+B Mac) |

### Common Terminal Commands

```bash
# Navigation
cd <directory>   # Change directory
ls               # List files
pwd              # Print working directory

# File Operations
cp <src> <dst>   # Copy
mv <src> <dst>   # Move/rename
rm <file>        # Delete file
mkdir <dir>      # Create directory

# Git
git status       # Check status
git log          # View commits
git pull         # Pull changes
git push         # Push commits

# Package Managers
npm install      # Install Node packages
pip install      # Install Python packages
```

---

**Happy Coding! 🚀**

*For technical support, email: support@youarecoder.com*
