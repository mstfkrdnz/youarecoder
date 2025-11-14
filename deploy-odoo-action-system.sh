#!/bin/bash
set -e

echo "🚀 Deploying Odoo Action-Based System to Production..."

PROD_SERVER="root@37.27.21.167"
PROD_PATH="/var/www/youarecoder"

echo ""
echo "📦 Step 1: Copying updated files to production..."

# Copy action handlers
echo "  → SystemdServiceActionHandler..."
scp app/services/action_handlers/systemd_service.py $PROD_SERVER:$PROD_PATH/app/services/action_handlers/

# Copy TraefikManager
echo "  → TraefikManager..."
scp app/services/traefik_manager.py $PROD_SERVER:$PROD_PATH/app/services/

# Copy WorkspaceProvisioner
echo "  → WorkspaceProvisioner..."
scp app/services/workspace_provisioner.py $PROD_SERVER:$PROD_PATH/app/services/

# Copy models (for get_metadata method)
echo "  → Models..."
scp app/models.py $PROD_SERVER:$PROD_PATH/app/

# Copy new template
echo "  → Odoo Action-Based Template..."
scp seeds/odoo_18_action_based_template.json $PROD_SERVER:$PROD_PATH/seeds/

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
ssh $PROD_SERVER "journalctl -u youarecoder -n 20 --no-pager"

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📝 Next Steps:"
echo "  1. Load the new template into database:"
echo "     ssh $PROD_SERVER"
echo "     cd $PROD_PATH"
echo "     source venv/bin/activate"
echo "     python3 seeds/load_template.py seeds/odoo_18_action_based_template.json"
echo ""
echo "  2. Create a test workspace to validate:"
echo "     - SSH: ssh $PROD_SERVER"
echo "     - Database: Check workspace_templates table"
echo "     - Create workspace via UI"
echo "     - Verify both URLs work:"
echo "       • Code: https://[workspace].youarecoder.com"
echo "       • Odoo: https://[workspace]-odoo.youarecoder.com"
echo ""
