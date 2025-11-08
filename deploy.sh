#!/bin/bash

# YouAreCoder Deployment Script
# Deploys code from local to production server

set -e  # Exit on error

# Configuration
PROD_SERVER="root@37.27.21.167"
PROD_PATH="/root/youarecoder"
LOCAL_PATH="/home/mustafa/youarecoder"

echo "🚀 Starting deployment to production..."

# Step 1: Ensure we're on main branch
echo "📌 Checking Git branch..."
cd "$LOCAL_PATH"
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "❌ Error: Not on main branch. Currently on: $CURRENT_BRANCH"
    exit 1
fi

# Step 2: Ensure working directory is clean
echo "🔍 Checking working directory..."
if ! git diff-index --quiet HEAD --; then
    echo "❌ Error: Working directory has uncommitted changes"
    echo "Please commit or stash your changes before deploying"
    git status
    exit 1
fi

# Step 3: Push to Git (if remote exists)
echo "📤 Pushing to Git..."
if git remote get-url origin &> /dev/null; then
    git push origin main
    echo "✅ Pushed to Git remote"
else
    echo "⚠️  No Git remote configured, skipping push"
fi

# Step 4: Sync files to production server
echo "📦 Syncing files to production server..."
rsync -avz --delete \
    --exclude='.git/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='venv/' \
    --exclude='claudedocs/' \
    --exclude='instance/' \
    --exclude='*.log' \
    "$LOCAL_PATH/" "$PROD_SERVER:$PROD_PATH/"

echo "✅ Files synced to production"

# Step 5: Run database migrations
echo "🗄️  Running database migrations..."
ssh "$PROD_SERVER" "cd $PROD_PATH && source venv/bin/activate && FLASK_APP=app flask db upgrade"
echo "✅ Database migrations complete"

# Step 6: Restart services
echo "🔄 Restarting services..."
ssh "$PROD_SERVER" "sudo systemctl restart youarecoder gunicorn"
echo "✅ Services restarted"

# Step 7: Verify deployment
echo "🔍 Verifying deployment..."
sleep 3
HEALTH_CHECK=$(ssh "$PROD_SERVER" "curl -s -o /dev/null -w '%{http_code}' http://localhost:5001/health" || echo "000")

if [ "$HEALTH_CHECK" = "200" ]; then
    echo "✅ Deployment successful! Application is healthy"
else
    echo "⚠️  Warning: Health check returned status $HEALTH_CHECK"
    echo "Please verify the application manually"
fi

echo ""
echo "🎉 Deployment complete!"
echo ""
echo "📊 Deployment Summary:"
echo "  • Branch: $CURRENT_BRANCH"
echo "  • Server: $PROD_SERVER"
echo "  • Path: $PROD_PATH"
echo "  • Health: $HEALTH_CHECK"
echo ""
