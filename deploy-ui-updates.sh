#!/bin/bash
set -e

echo "🚀 Deploying UI updates for workspace template action sequences..."

# Production server
SERVER="root@37.27.21.167"
APP_DIR="/root/youarecoder"

echo "📦 Step 1: Transfer updated files to production..."
rsync -avz --progress \
    app/templates/admin/template_form.html \
    app/templates/admin/templates.html \
    app/routes/admin.py \
    app/models.py \
    "${SERVER}:${APP_DIR}/"

echo "🔄 Step 2: Restart Flask application..."
ssh $SERVER "cd $APP_DIR && supervisorctl restart youarecoder"

echo "⏳ Waiting for application to restart..."
sleep 5

echo "✅ Step 3: Verify application is running..."
ssh $SERVER "supervisorctl status youarecoder"

echo ""
echo "✅ UI deployment completed successfully!"
echo "🌐 Access the updated UI at: https://youarecoder.com/admin/templates"
echo ""
echo "📝 Changes deployed:"
echo "  • Added rollback_on_fatal_error checkbox to template form"
echo "  • Added action sequence management UI"
echo "  • Updated backend routes to handle action sequences CRUD"
echo "  • Updated WorkspaceTemplate.to_dict() to include action_sequences"
echo "  • Updated templates list to show action count and rollback status"
