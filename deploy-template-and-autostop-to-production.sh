#!/bin/bash

# Template Provisioning and Auto-Stop Scheduler - Production Deployment Script
# Deploys code and sets up systemd timer for auto-stop scheduler

set -e  # Exit on any error

SERVER="root@37.27.21.167"
PASSWORD="tR\$8vKz3&Pq9y#M2x7!hB5s"
APP_DIR="/opt/youarecoder"

echo "🚀 Template Provisioning & Auto-Stop Deployment"
echo "=================================================="
echo ""

# Step 1: Git operations on production
echo "📦 Step 1: Pulling latest code from repository..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER" << 'ENDSSH'
cd /opt/youarecoder

# Stash any local changes
git stash

# Pull latest code
git pull origin main

echo "✅ Code pulled successfully"
ENDSSH

# Step 2: Install Flask CLI and verify
echo ""
echo "🔧 Step 2: Verifying Flask CLI commands..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER" << 'ENDSSH'
cd /opt/youarecoder
source venv/bin/activate

# Test Flask CLI command availability
flask --help | grep auto-stop-check > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ Flask CLI command 'auto-stop-check' registered successfully"
else
    echo "❌ Flask CLI command registration failed"
    exit 1
fi
ENDSSH

# Step 3: Setup systemd timer for auto-stop scheduler
echo ""
echo "⏰ Step 3: Setting up systemd timer for auto-stop scheduler..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER" << 'ENDSSH'
# Copy systemd files
cp /opt/youarecoder/systemd/youarecoder-auto-stop.service /etc/systemd/system/
cp /opt/youarecoder/systemd/youarecoder-auto-stop.timer /etc/systemd/system/

# Reload systemd
systemctl daemon-reload

# Enable and start timer
systemctl enable youarecoder-auto-stop.timer
systemctl start youarecoder-auto-stop.timer

# Check timer status
systemctl status youarecoder-auto-stop.timer --no-pager | head -10

echo "✅ Auto-stop scheduler timer configured"
ENDSSH

# Step 4: Restart Flask application
echo ""
echo "🔄 Step 4: Restarting Flask application..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER" << 'ENDSSH'
sudo systemctl restart youarecoder
sleep 2

# Check if service is running
if systemctl is-active --quiet youarecoder; then
    echo "✅ Flask application restarted successfully"
else
    echo "❌ Flask application failed to start"
    sudo systemctl status youarecoder
    exit 1
fi
ENDSSH

# Step 5: Verify deployment
echo ""
echo "🔍 Step 5: Verifying deployment..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER" << 'ENDSSH'
cd /opt/youarecoder
source venv/bin/activate

# Test auto-stop scheduler (dry run)
echo "Testing auto-stop scheduler..."
flask auto-stop-check

echo ""
echo "✅ Deployment verification complete"
ENDSSH

# Step 6: Display timer schedule
echo ""
echo "📅 Step 6: Displaying auto-stop timer schedule..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER" << 'ENDSSH'
systemctl list-timers --no-pager | grep youarecoder-auto-stop
ENDSSH

echo ""
echo "=================================================="
echo "✅ Template Provisioning & Auto-Stop Deployment Complete!"
echo ""
echo "New Features Available:"
echo "  - Workspace template application during provisioning"
echo "  - Template selection in workspace creation form"
echo "  - Package installation (pip3)"
echo "  - VS Code extension installation"
echo "  - Git repository cloning"
echo "  - VS Code settings application"
echo "  - Environment variables injection"
echo "  - Post-creation script execution"
echo ""
echo "Auto-Stop Scheduler:"
echo "  - Systemd timer: youarecoder-auto-stop.timer"
echo "  - Runs every: 15 minutes"
echo "  - Manual run: flask auto-stop-check"
echo "  - Check status: systemctl status youarecoder-auto-stop.timer"
echo "  - View logs: journalctl -u youarecoder-auto-stop.service"
echo ""
echo "🌐 Production: https://youarecoder.com"
echo "=================================================="
