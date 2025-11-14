#!/bin/bash
set -e

echo "🚀 Deploying Odoo Provisioning Fixes to Production..."

PROD_SERVER="root@37.27.21.167"
PROD_PATH="/var/www/youarecoder"

echo ""
echo "📦 Step 1: Copying fixed action handlers to production..."

# Copy pip_requirements handler (Fix 4: handle missing requirements.txt)
echo "  → pip_requirements.py (Fix 4: graceful requirements.txt handling)..."
scp app/services/action_handlers/pip_requirements.py $PROD_SERVER:$PROD_PATH/app/services/action_handlers/

# Copy python_venv handler (Fix 3: proper venv ownership)
echo "  → python_venv.py (Fix 3: venv ownership)..."
scp app/services/action_handlers/python_venv.py $PROD_SERVER:$PROD_PATH/app/services/action_handlers/

# Copy CLI commands (for any Flask command updates)
echo "  → cli.py..."
scp app/cli.py $PROD_SERVER:$PROD_PATH/app/

echo ""
echo "🔄 Step 2: Restarting Flask application..."
ssh $PROD_SERVER "systemctl restart youarecoder"

echo ""
echo "⏳ Step 3: Waiting for application to start..."
sleep 5

echo ""
echo "✅ Step 4: Verifying deployment..."
ssh $PROD_SERVER "systemctl status youarecoder --no-pager | head -n 20"

echo ""
echo "📊 Step 5: Checking application logs..."
ssh $PROD_SERVER "journalctl -u youarecoder -n 30 --no-pager"

echo ""
echo "🔍 Step 6: Verifying fixes are deployed..."
echo ""
echo "Checking Fix 4 (pip_requirements.py graceful error handling):"
ssh $PROD_SERVER "grep -A 8 'if not os.path.exists(requirements_file)' $PROD_PATH/app/services/action_handlers/pip_requirements.py | head -10"

echo ""
echo "Checking Fix 3 (python_venv.py ownership):"
ssh $PROD_SERVER "grep -A 5 'sudo -u' $PROD_PATH/app/services/action_handlers/python_venv.py | head -8"

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📝 Summary of fixes deployed:"
echo "  ✅ Fix 3: Python venv creation with proper ownership (sudo -u)"
echo "  ✅ Fix 4: Graceful handling of missing requirements.txt files"
echo ""
echo "🧪 Next step: Create a new test workspace (w442+) to validate all fixes"
echo ""
