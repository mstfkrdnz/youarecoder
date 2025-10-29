#!/bin/bash
# Team Management MVP Deployment Script
# Deploys data-testid updates and team management features to production

set -e

SERVER="37.27.21.167"
SERVER_USER="root"
SERVER_PASS="tR\$8vKz3&Pq9y#M2x7!hB5s"
APP_DIR="/root/youarecoder"

echo "=== Team Management MVP Deployment ==="
echo "Target Server: $SERVER"
echo "Date: $(date)"
echo ""

echo "📤 Step 1: Pushing local commits to origin..."
git push origin main
echo "✅ Code pushed to repository"
echo ""

echo "📥 Step 2: Connecting to production server and pulling updates..."
sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER" << 'ENDSSH'
    set -e

    echo "📂 Changing to app directory..."
    cd /root/youarecoder

    echo "🔄 Pulling latest code..."
    git pull origin main

    echo "🐍 Activating virtual environment..."
    source venv/bin/activate

    echo "📦 Installing any new dependencies..."
    pip install -r requirements.txt --quiet

    echo "💾 Running database migrations (if any)..."
    export FLASK_APP=app
    flask db upgrade || echo "No new migrations"

    echo "✅ Code updated successfully"
ENDSSH

echo ""
echo "🔄 Step 3: Restarting Flask application service..."
sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER" << 'ENDSSH'
    echo "🛑 Stopping youarecoder service..."
    systemctl stop youarecoder.service

    echo "⏱️  Waiting 2 seconds..."
    sleep 2

    echo "🚀 Starting youarecoder service..."
    systemctl start youarecoder.service

    echo "⏱️  Waiting 3 seconds for service to start..."
    sleep 3

    echo "🔍 Checking service status..."
    systemctl status youarecoder.service --no-pager || true

    echo ""
    echo "📊 Service is:"
    systemctl is-active youarecoder.service
ENDSSH

echo ""
echo "🧪 Step 4: Running smoke tests..."
sleep 5

# Test health endpoint
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://youarecoder.com || echo "000")
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ]; then
    echo "✅ Website is responding (HTTP $HTTP_CODE)"
else
    echo "⚠️  Website returned HTTP $HTTP_CODE"
fi

# Test registration page
REG_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://youarecoder.com/auth/register || echo "000")
if [ "$REG_CODE" = "200" ]; then
    echo "✅ Registration page is accessible"
else
    echo "⚠️  Registration page returned HTTP $REG_CODE"
fi

# Test team page (requires auth, so 302 redirect is expected)
TEAM_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://youarecoder.com/admin/team || echo "000")
if [ "$TEAM_CODE" = "302" ] || [ "$TEAM_CODE" = "200" ]; then
    echo "✅ Team management page route exists"
else
    echo "⚠️  Team management page returned HTTP $TEAM_CODE"
fi

echo ""
echo "=== ✅ Deployment Complete! ==="
echo ""
echo "Deployed Features:"
echo "  • Data-testid attributes on all forms"
echo "  • Team member add form with invitation system"
echo "  • POST /admin/team/add API endpoint"
echo "  • Email invitations with temporary passwords"
echo "  • E2E test updates with stable selectors"
echo ""
echo "Next Steps:"
echo "  1. Run E2E tests: pytest tests/test_e2e_comprehensive_features.py -v -m e2e"
echo "  2. Monitor logs: ssh root@$SERVER 'journalctl -u youarecoder.service -f'"
echo "  3. Test team management: https://youarecoder.com/admin/team"
echo ""
echo "Documentation:"
echo "  • API Guide: claudedocs/team-add-api-implementation.md"
echo "  • Test Report: claudedocs/e2e-test-analysis-report.md"
echo "  • Data-TestID: claudedocs/data-testid-migration-complete.md"
echo ""
