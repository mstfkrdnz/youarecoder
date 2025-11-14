#!/bin/bash
set -e

echo "🚀 Deploying Billing System to Production"
echo "=========================================="

# Configuration
PROD_SERVER="37.27.21.167"
PROD_USER="root"
PROD_PASS="tR\$8vKz3&Pq9y#M2x7!hB5s"
PROD_PATH="/opt/youarecoder"

echo ""
echo "📦 Step 1: Transferring files..."
sshpass -p "$PROD_PASS" scp -r app/ $PROD_USER@$PROD_SERVER:$PROD_PATH/
sshpass -p "$PROD_PASS" scp -r migrations/ $PROD_USER@$PROD_SERVER:$PROD_PATH/
echo "✅ Files transferred"

echo ""
echo "🗄️  Step 2: Running database migration..."
sshpass -p "$PROD_PASS" ssh $PROD_USER@$PROD_SERVER << 'ENDSSH'
cd /opt/youarecoder
source venv/bin/activate
flask db upgrade
echo "✅ Migration complete"
ENDSSH

echo ""
echo "🔄 Step 3: Restarting Flask application..."
sshpass -p "$PROD_PASS" ssh $PROD_USER@$PROD_SERVER << 'ENDSSH'
systemctl restart youarecoder
sleep 3
systemctl status youarecoder --no-pager -l
echo "✅ Service restarted"
ENDSSH

echo ""
echo "✨ Step 4: Verifying deployment..."
sleep 2

# Test billing endpoint
RESPONSE_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://youarecoder.com/billing/)
echo "Billing endpoint response: $RESPONSE_CODE"

if [ "$RESPONSE_CODE" = "404" ]; then
    echo "❌ DEPLOYMENT FAILED: Billing routes still returning 404"
    exit 1
elif [ "$RESPONSE_CODE" = "302" ] || [ "$RESPONSE_CODE" = "200" ]; then
    echo "✅ DEPLOYMENT SUCCESS: Billing routes accessible"
else
    echo "⚠️  Unexpected response code: $RESPONSE_CODE"
fi

echo ""
echo "=========================================="
echo "🎉 Billing System Deployment Complete!"
echo "=========================================="
echo ""
echo "📋 Next Steps:"
echo "1. Configure PayTR credentials in production .env file"
echo "2. Test subscription flow manually"
echo "3. Re-run E2E tests to verify production deployment"
echo ""
