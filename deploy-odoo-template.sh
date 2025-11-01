#!/bin/bash
# Deployment script for Odoo 18.4 Template System
# Run this on production server: ssh root@37.27.21.167 'bash -s' < deploy-odoo-template.sh

set -e  # Exit on error

echo "🚀 Deploying Odoo 18.4 Template System..."

# Navigate to project directory
cd /home/mustafa/youarecoder || exit 1

echo "📥 Pulling latest changes from repository..."
sudo -u mustafa git pull origin main

echo "🗄️  Running database migrations..."
sudo -u postgres psql -d youarecoder -c "ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS access_token VARCHAR(64) UNIQUE;"
sudo -u postgres psql -d youarecoder -c "ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS ssh_public_key TEXT;"

echo "📦 Seeding Odoo 18.4 template..."
sudo -u mustafa python3 seed_odoo_production.py

echo "🔄 Restarting youarecoder service..."
systemctl restart youarecoder

echo "✅ Deployment complete!"
echo ""
echo "🔍 Service status:"
systemctl status youarecoder --no-pager | head -10
