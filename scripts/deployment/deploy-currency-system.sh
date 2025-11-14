#!/bin/bash
# Deploy Dynamic Currency System to Production
# Usage: ./deploy-currency-system.sh

set -e

SERVER="root@37.27.21.167"
PROJECT_DIR="/root/youarecoder"

echo "================================================"
echo "🚀 Deploying Dynamic Currency System"
echo "================================================"

# Step 1: Deploy Code
echo ""
echo "📦 Step 1/6: Deploying code to production..."
ssh $SERVER "cd $PROJECT_DIR && git pull && sudo systemctl restart youarecoder"
echo "✅ Code deployed successfully"

# Step 2: Run Migration
echo ""
echo "🗄️  Step 2/6: Running database migration..."
ssh $SERVER << 'EOF'
cd /var/www/youarecoder
source venv/bin/activate
FLASK_APP=app FLASK_ENV=production flask db upgrade
EOF
echo "✅ Migration completed"

# Step 3: Fetch Initial Rates
echo ""
echo "💱 Step 3/6: Fetching initial exchange rates..."
ssh $SERVER << 'EOF'
cd /var/www/youarecoder
source venv/bin/activate
FLASK_APP=app FLASK_ENV=production flask update-exchange-rates
EOF
echo "✅ Exchange rates fetched"

# Step 4: Setup Cronjob
echo ""
echo "⏰ Step 4/6: Setting up cronjob..."
ssh $SERVER << 'EOF'
# Make script executable
chmod +x /var/www/youarecoder/scripts/update-exchange-rates.sh

# Create log directory
mkdir -p /var/log/youarecoder
chown youarecoder:youarecoder /var/log/youarecoder

# Remove existing exchange-rates cronjobs (if any)
crontab -l 2>/dev/null | grep -v exchange-rates | crontab - 2>/dev/null || true

# Add new cronjobs
(crontab -l 2>/dev/null; echo "0 16 * * * /var/www/youarecoder/scripts/update-exchange-rates.sh") | crontab -
(crontab -l 2>/dev/null; echo "0 17 * * * /var/www/youarecoder/scripts/update-exchange-rates.sh") | crontab -
(crontab -l 2>/dev/null; echo "0 18 * * * /var/www/youarecoder/scripts/update-exchange-rates.sh") | crontab -

echo "Cronjobs added:"
crontab -l | grep exchange-rates
EOF
echo "✅ Cronjob configured"

# Step 5: Verify Database
echo ""
echo "🔍 Step 5/6: Verifying database..."
ssh $SERVER 'sudo -u postgres psql -d youarecoder -c "SELECT source_currency, rate, effective_date FROM exchange_rates ORDER BY effective_date DESC LIMIT 3;"'
echo "✅ Database verified"

# Step 6: Check Application Status
echo ""
echo "📊 Step 6/6: Checking application status..."
ssh $SERVER 'sudo systemctl status youarecoder --no-pager | head -10'
echo "✅ Application running"

echo ""
echo "================================================"
echo "✅ DEPLOYMENT COMPLETE!"
echo "================================================"
echo ""
echo "📋 Next Steps:"
echo "  1. Visit https://youarecoder.com/billing"
echo "  2. Verify USD is selected by default"
echo "  3. Check exchange rate date displays"
echo "  4. Test currency switching (TRY, USD, EUR)"
echo "  5. Monitor logs: ssh $SERVER 'tail -f /var/log/youarecoder/exchange-rates.log'"
echo ""
echo "📊 Quick Checks:"
echo "  • Exchange rates: ssh $SERVER 'sudo -u postgres psql -d youarecoder -c \"SELECT * FROM exchange_rates ORDER BY effective_date DESC LIMIT 5;\"'"
echo "  • Cronjob status: ssh $SERVER 'crontab -l | grep exchange-rates'"
echo "  • Application logs: ssh $SERVER 'tail -f /var/log/youarecoder/exchange-rates.log'"
echo ""
