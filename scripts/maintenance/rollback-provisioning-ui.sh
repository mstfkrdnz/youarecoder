#!/bin/bash
# Rollback script - Provisioning UI'yi eski haline döndürür

echo "🔄 Rolling back provisioning.html to old version..."

# Find the backup file
BACKUP_FILE=$(ssh root@37.27.21.167 'ls -t /var/www/youarecoder/app/templates/workspace/provisioning.html.backup.before_deploy.* | head -1')

if [ -z "$BACKUP_FILE" ]; then
    echo "❌ Backup file not found!"
    exit 1
fi

echo "📦 Backup file: $BACKUP_FILE"

# Restore from backup
ssh root@37.27.21.167 "cp $BACKUP_FILE /var/www/youarecoder/app/templates/workspace/provisioning.html"

# Restart service
echo "🔄 Restarting Flask service..."
ssh root@37.27.21.167 'systemctl restart youarecoder'

echo "✅ Rollback completed!"
echo "🌐 Test at: https://youarecoder.com/workspace/105/provisioning"
