# YouAreCoder Deployment Guide

## 🚨 CRITICAL: Production Deployment Policy

**NEVER use `rsync`, `scp`, or manual file copying to production!**

All production deployments MUST go through GitHub to ensure:
- ✅ Code review and version control
- ✅ Automated testing before deployment
- ✅ Rollback capability
- ✅ Audit trail of all changes
- ✅ Consistent deployment process

## 🚀 Proper Deployment Workflow

### Development → Production Flow

```bash
# 1. Make your changes in development
cd /home/mustafa/youarecoder

# 2. Test locally
python3 run.py
# Visit: https://mustafa-youarecoder.dev.alkedos.com

# 3. Stage and commit changes
git add .
git commit -m "feat: your feature description"

# 4. Push to GitHub
git push origin main

# 5. GitHub Actions automatically deploys to production
# Monitor at: https://github.com/yourusername/youarecoder/actions
```

### Quick Deploy Helper

Use the built-in helper function:

```bash
# Source the aliases (add to ~/.bashrc for persistence)
source ~/.bash_aliases_youarecoder

# Interactive deployment
deploy-youarecoder
```

## 🔒 Safety Mechanisms

### 1. Shell Alias Protection
The `rsync` command is wrapped to block production server:
- Blocks: `rsync ... root@37.27.21.167:...`
- Allows: `rsync` to other destinations
- Override (emergency): `command rsync ...`

### 2. Git Pre-commit Hook
Prevents committing files with:
- `rsync` commands targeting production (37.27.21.167)
- Hardcoded credentials
- Override (emergency): `git commit --no-verify`

### 3. SSH Warning
SSHing to production shows a reminder about GitHub workflow

## 📋 GitHub Actions Deployment (To Be Configured)

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Deploy to Production
        env:
          SSH_PRIVATE_KEY: ${{ secrets.DEPLOY_SSH_KEY }}
          PRODUCTION_HOST: 37.27.21.167
        run: |
          # Setup SSH
          mkdir -p ~/.ssh
          echo "$SSH_PRIVATE_KEY" > ~/.ssh/deploy_key
          chmod 600 ~/.ssh/deploy_key

          # Deploy via SSH (controlled by GitHub)
          ssh -i ~/.ssh/deploy_key root@$PRODUCTION_HOST << 'EOF'
            cd /var/www/youarecoder
            git pull origin main
            source venv/bin/activate
            pip install -r requirements.txt
            flask db upgrade
            sudo systemctl restart youarecoder
          EOF
```

## 🆘 Emergency Direct Access

If you MUST bypass safety mechanisms (system down, emergency fix):

### Emergency rsync
```bash
command rsync -avz --delete \
  --exclude='.git' \
  --exclude='venv' \
  --exclude='*.pyc' \
  /home/mustafa/youarecoder/ \
  root@37.27.21.167:/var/www/youarecoder/
```

### Emergency commit
```bash
git commit --no-verify -m "EMERGENCY: description"
```

**⚠️ WARNING**: Document emergency deployments and create proper GitHub commits ASAP after emergency.

## 📊 Deployment Checklist

Before pushing to GitHub (triggers production deploy):

- [ ] Tests pass locally
- [ ] Database migrations created if needed (`flask db migrate`)
- [ ] `.env` changes documented (don't commit .env itself!)
- [ ] No hardcoded credentials in code
- [ ] Changelog/commit message is descriptive
- [ ] Reviewed diff: `git diff`

## 🔄 Rollback Procedure

If deployment breaks production:

```bash
# GitHub approach (recommended)
git revert HEAD
git push origin main
# GitHub Actions deploys the revert

# Or rollback to specific commit
git log  # find working commit hash
git revert <bad-commit-hash>
git push origin main
```

## 📁 Files Never to Commit

- `.env` (use `.env.example` instead)
- `venv/` (in `.gitignore`)
- `*.pyc`, `__pycache__/` (in `.gitignore`)
- Database files (`*.db`)
- Secret keys, API keys, passwords

## 🛠️ Setup Instructions

### 1. Activate Shell Protections

Add to `~/.bashrc`:
```bash
# YouAreCoder deployment safety
if [ -f ~/.bash_aliases_youarecoder ]; then
    source ~/.bash_aliases_youarecoder
fi
```

Then reload:
```bash
source ~/.bashrc
```

### 2. Verify Git Hook

```bash
ls -la /home/mustafa/youarecoder/.git/hooks/pre-commit
# Should be executable (-rwxr-xr-x)
```

### 3. Test Protection

```bash
# This should be BLOCKED:
rsync -avz ./ root@37.27.21.167:/var/www/youarecoder/

# Should show error and reminder to use GitHub
```

## 📞 Support

If you encounter deployment issues:
1. Check GitHub Actions logs
2. Review this deployment guide
3. Check production server logs: `ssh root@37.27.21.167 'sudo journalctl -u youarecoder -n 50'`
4. Verify .env configuration on production

## 🎯 TL;DR

```bash
# ✅ RIGHT WAY
git add .
git commit -m "your changes"
git push origin main
# → GitHub Actions deploys

# ❌ WRONG WAY
rsync ... root@37.27.21.167:...  # BLOCKED!
scp ... root@37.27.21.167:...     # DON'T DO THIS!
```

**Remember: Friends don't let friends rsync to production! 🚫**
