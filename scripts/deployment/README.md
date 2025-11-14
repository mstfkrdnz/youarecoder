# YouAreCoder Production Deployment

## Overview

This directory contains scripts for safely deploying YouAreCoder to production via GitHub.

## Files

- `deploy-to-production.sh` - Main deployment script
- `rollback-production.sh` - Rollback to previous commit
- `README.md` - This file

## Prerequisites

1. All changes committed and pushed to GitHub
2. SSH access to production server (37.27.21.167)
3. Production server has Git configured
4. systemd service `youarecoder` configured on production

## Usage

### Standard Deployment

```bash
cd /home/mustafa/youarecoder
./scripts/deployment/deploy-to-production.sh
```

**Prompts**:
- Confirms you're on `main` branch
- Checks for uncommitted changes
- Verifies local is synced with GitHub
- Shows commit to be deployed
- Asks for confirmation before deploying

### Dry Run (Test Without Changes)

```bash
./scripts/deployment/deploy-to-production.sh --dry-run
```

This shows what would happen without making any changes.

### Rollback to Previous Version

```bash
./scripts/deployment/rollback-production.sh
```

Rolls back to the commit that was active before the last deployment.

## Deployment Process

The script performs these steps on production:

1. **Backup**: Saves current commit hash for rollback
2. **Pull**: Fetches latest from GitHub (`origin/main`)
3. **Dependencies**: Installs/updates Python packages
4. **Migrations**: Runs database migrations
5. **Restart**: Restarts the systemd service
6. **Verify**: Checks service is running
7. **Rollback**: If service fails, automatically rolls back

## Safety Features

- ✅ Pre-flight checks (uncommitted changes, branch, sync)
- ✅ Confirmation prompt before deployment
- ✅ Automatic rollback on service failure
- ✅ Dry-run mode for testing
- ✅ Deployment log with timestamps
- ✅ Previous commit saved for manual rollback

## Troubleshooting

### Service Failed to Start

If deployment fails and auto-rollback occurs:

1. SSH to production: `ssh root@37.27.21.167`
2. Check logs: `sudo journalctl -u youarecoder -n 50`
3. Check service status: `sudo systemctl status youarecoder`
4. Fix issue locally, commit, push, redeploy

### Manual Rollback

```bash
ssh root@37.27.21.167
cd /var/www/youarecoder
PREV_COMMIT=$(cat /tmp/youarecoder_previous_commit.txt)
git reset --hard $PREV_COMMIT
sudo systemctl restart youarecoder
```

### Stuck Deployment

If deployment hangs:
1. Ctrl+C to cancel
2. SSH to production and check status
3. Manually restart service if needed
4. Check logs for issues

## Best Practices

1. **Always test locally first**: Ensure changes work in development
2. **Deploy during low-traffic times**: Minimize user impact
3. **Monitor after deployment**: Check logs and site functionality
4. **Use dry-run first**: Test the deployment process
5. **Keep commits small**: Easier to identify and rollback issues

## Emergency Contact

If production is down and deployment fails:

1. Use rollback script immediately
2. Check service logs
3. If rollback fails, SSH and manually restart
4. Document the issue for post-mortem
