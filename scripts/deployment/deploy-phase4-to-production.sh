#!/bin/bash

# Phase 4: Workspace Lifecycle Management - Production Deployment Script
# Deploys migration 007 and application code to production server

set -e  # Exit on any error

SERVER="root@37.27.21.167"
PASSWORD="tR\$8vKz3&Pq9y#M2x7!hB5s"
APP_DIR="/opt/youarecoder"

echo "🚀 Phase 4 Deployment: Workspace Lifecycle Management"
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

# Step 2: Run database migration 007
echo ""
echo "🗄️  Step 2: Running database migration 007..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER" << 'ENDSSH'
cd /opt/youarecoder

# Activate virtual environment and run migration
source venv/bin/activate

# Run migration via Python script
python3 - <<'MIGRATION'
import sys
sys.path.insert(0, '/opt/youarecoder')

from app import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    print("  Running migration 007: Add workspace lifecycle management fields...")

    # Add lifecycle tracking columns
    db.session.execute(text("""
        ALTER TABLE workspaces
        ADD COLUMN IF NOT EXISTS is_running BOOLEAN NOT NULL DEFAULT false
    """))

    db.session.execute(text("""
        ALTER TABLE workspaces
        ADD COLUMN IF NOT EXISTS last_started_at TIMESTAMP
    """))

    db.session.execute(text("""
        ALTER TABLE workspaces
        ADD COLUMN IF NOT EXISTS last_stopped_at TIMESTAMP
    """))

    db.session.execute(text("""
        ALTER TABLE workspaces
        ADD COLUMN IF NOT EXISTS last_accessed_at TIMESTAMP
    """))

    # Add resource management columns
    db.session.execute(text("""
        ALTER TABLE workspaces
        ADD COLUMN IF NOT EXISTS auto_stop_hours INTEGER NOT NULL DEFAULT 0
    """))

    db.session.execute(text("""
        ALTER TABLE workspaces
        ADD COLUMN IF NOT EXISTS cpu_limit_percent INTEGER NOT NULL DEFAULT 100
    """))

    db.session.execute(text("""
        ALTER TABLE workspaces
        ADD COLUMN IF NOT EXISTS memory_limit_mb INTEGER NOT NULL DEFAULT 2048
    """))

    # Create indexes
    db.session.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_workspaces_is_running
        ON workspaces(is_running)
    """))

    db.session.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_workspaces_last_accessed_at
        ON workspaces(last_accessed_at)
    """))

    db.session.commit()
    print("  ✅ Migration 007 completed successfully")
    print("     - Added: is_running, last_started_at, last_stopped_at, last_accessed_at")
    print("     - Added: auto_stop_hours, cpu_limit_percent, memory_limit_mb")
    print("     - Created indexes for lifecycle queries")
MIGRATION

echo "✅ Migration 007 completed"
ENDSSH

# Step 3: Restart Flask application
echo ""
echo "🔄 Step 3: Restarting Flask application..."
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

# Step 4: Verify deployment
echo ""
echo "🔍 Step 4: Verifying deployment..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER" << 'ENDSSH'
cd /opt/youarecoder
source venv/bin/activate

# Verify database schema
python3 - <<'VERIFY'
import sys
sys.path.insert(0, '/opt/youarecoder')

from app import create_app, db
from sqlalchemy import text, inspect

app = create_app()
with app.app_context():
    inspector = inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns('workspaces')]

    # Check for new lifecycle fields
    lifecycle_fields = [
        'is_running', 'last_started_at', 'last_stopped_at',
        'last_accessed_at', 'auto_stop_hours', 'cpu_limit_percent',
        'memory_limit_mb'
    ]

    missing_fields = [field for field in lifecycle_fields if field not in columns]

    if missing_fields:
        print(f"  ❌ Missing fields: {', '.join(missing_fields)}")
        sys.exit(1)
    else:
        print("  ✅ All lifecycle fields present in database")

    # Check indexes
    indexes = inspector.get_indexes('workspaces')
    index_names = [idx['name'] for idx in indexes]

    required_indexes = ['ix_workspaces_is_running', 'ix_workspaces_last_accessed_at']
    missing_indexes = [idx for idx in required_indexes if idx not in index_names]

    if missing_indexes:
        print(f"  ⚠️  Missing indexes: {', '.join(missing_indexes)}")
    else:
        print("  ✅ All lifecycle indexes created")

    print("\n  📊 Database verification complete")
VERIFY
ENDSSH

echo ""
echo "=================================================="
echo "✅ Phase 4 Deployment Complete!"
echo ""
echo "New Features Available:"
echo "  - Workspace Start/Stop/Restart controls"
echo "  - Real-time workspace status tracking"
echo "  - Code-server logs viewer"
echo "  - Lifecycle timestamps (started/stopped/accessed)"
echo "  - Resource limits configuration"
echo ""
echo "API Endpoints:"
echo "  - POST /workspace/<id>/start"
echo "  - POST /workspace/<id>/stop"
echo "  - POST /workspace/<id>/restart"
echo "  - GET  /workspace/<id>/status"
echo "  - GET  /workspace/<id>/logs"
echo ""
echo "🌐 Production: https://youarecoder.com"
echo "=================================================="
