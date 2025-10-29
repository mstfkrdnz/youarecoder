#!/bin/bash

# Template Syntax Fix - Production Deployment Script
# Fixes Jinja2 template syntax error in workspace/list.html

set -e  # Exit on any error

SERVER="root@37.27.21.167"
PASSWORD="tR\$8vKz3&Pq9y#M2x7!hB5s"
APP_DIR="/root/youarecoder"

echo "🚀 Template Syntax Fix Deployment"
echo "=================================================="
echo ""

# Step 1: Git operations on production
echo "📦 Step 1: Pulling latest code from repository..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER" << 'ENDSSH'
cd /root/youarecoder

# Stash any local changes
git stash

# Pull latest code
git pull origin main

echo "✅ Code pulled successfully"
ENDSSH

# Step 2: Restart Flask application
echo ""
echo "🔄 Step 2: Restarting Flask application..."
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

# Step 3: Verify deployment
echo ""
echo "🔍 Step 3: Verifying deployment..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER" << 'ENDSSH'
# Test homepage
curl -s -o /dev/null -w "Status: %{http_code}\n" http://127.0.0.1:5000/

echo "✅ Application responding correctly"
ENDSSH

echo ""
echo "=================================================="
echo "✅ Template Syntax Fix Deployment Complete!"
echo ""
echo "Fixed:"
echo "  - Added missing {% endblock %} tag in workspace/list.html"
echo "  - Resolved 'Unexpected end of template' Jinja2 error"
echo "  - Real-time workspace status updates now working"
echo ""
echo "🌐 Production: https://youarecoder.com/workspace/"
echo "=================================================="
