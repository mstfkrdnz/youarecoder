#!/bin/bash
# Deployment script for Odoo 18.4 Template System
# Run locally: ./deploy-odoo-template.sh

set -e  # Exit on error

echo "🚀 Deploying Odoo 18.4 Template System to Production..."

# Create deployment tarball
echo "📦 Creating deployment tarball..."
tar czf youarecoder_odoo_template.tar.gz \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    app/ \
    seeds/ \
    seed_odoo_template.sql \
    config/ \
    migrations/

echo "📤 Uploading to server..."
scp youarecoder_odoo_template.tar.gz root@37.27.21.167:/tmp/

echo "🔧 Extracting and deploying on server..."
ssh root@37.27.21.167 << 'EOF'
    cd /home/mustafa/youarecoder
    tar xzf /tmp/youarecoder_odoo_template.tar.gz
    rm /tmp/youarecoder_odoo_template.tar.gz

    echo "🗄️  Running database migrations..."
    sudo -u postgres psql -d youarecoder -c "ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS access_token VARCHAR(64) UNIQUE;" 2>/dev/null || true
    sudo -u postgres psql -d youarecoder -c "ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS ssh_public_key TEXT;" 2>/dev/null || true

    echo "📦 Seeding Odoo 18.4 template..."
    sudo -u postgres psql -d youarecoder -f seed_odoo_template.sql

    echo "🔄 Restarting youarecoder service..."
    systemctl restart youarecoder

    echo "✅ Deployment complete!"
    echo ""
    echo "🔍 Service status:"
    systemctl status youarecoder --no-pager | head -10
EOF

echo "🧹 Cleaning up local tarball..."
rm youarecoder_odoo_template.tar.gz

echo "✅ Deployment script completed successfully!"
