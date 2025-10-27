# Billing System Production Deployment Guide

**Status:** Code ready locally, awaiting production deployment
**Target Server:** 37.27.21.167
**Priority:** CRITICAL - Billing system functional but not deployed

---

## Current Situation

### ✅ Code Status (Local Development)
- Billing blueprint registered in `app/__init__.py` (lines 100, 105, 108)
- All billing templates exist in `app/templates/billing/`
- 28/28 unit tests passing (100%)
- Code coverage: 85% (billing routes), 78% (PayTR service)
- Email notifications integrated

### ❌ Production Status
- Billing routes return 404 on production
- Code not deployed to 37.27.21.167
- Production users cannot access billing system

---

## Pre-Deployment Checklist

### 1. Code Verification (Already Complete ✅)
- [x] Billing blueprint registered
- [x] Templates exist (success.html, fail.html, dashboard.html)
- [x] PayTR service implemented
- [x] Email notifications integrated
- [x] Unit tests passing
- [x] Database migration created (003_add_billing_models.py)

### 2. Environment Configuration Required
- [ ] PayTR credentials on production server
- [ ] Database migration applied
- [ ] Flask app restarted

---

## Deployment Steps

### Step 1: Push Code to Production Server

```bash
# From local machine (this machine)
cd /home/mustafa/youarecoder

# Ensure latest code is committed to git
git status
git add app/__init__.py app/routes/billing.py app/services/paytr_service.py
git add app/templates/billing/
git add migrations/versions/003_add_billing_models.py
git commit -m "Add: PayTR billing system with email notifications

- Complete billing blueprint with 5 endpoints
- PayTR API integration (HMAC-SHA256 security)
- 3 subscription plans (Starter/Team/Enterprise)
- 14-day trial period support
- Email notifications (success/failure/trial expiry)
- Database models: Subscription, Payment, Invoice
- 28 unit tests (100% pass rate)
- 85% code coverage

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"

# Push to production server (if using git deployment)
git push production main

# OR use SCP to transfer files directly
sshpass -p 'tR$8vKz3&Pq9y#M2x7!hB5s' scp -r app/ root@37.27.21.167:/opt/youarecoder/
sshpass -p 'tR$8vKz3&Pq9y#M2x7!hB5s' scp -r migrations/ root@37.27.21.167:/opt/youarecoder/
```

### Step 2: Configure Environment Variables on Production

```bash
# SSH to production server
ssh root@37.27.21.167

# Add PayTR configuration to environment file
cat >> /opt/youarecoder/.env << 'EOF'

# PayTR Payment Gateway Configuration
PAYTR_MERCHANT_ID=your_merchant_id_here
PAYTR_MERCHANT_KEY=your_merchant_key_here
PAYTR_MERCHANT_SALT=your_merchant_salt_here
PAYTR_TEST_MODE=1  # Set to 0 for production payments
EOF

# Secure the environment file
chmod 600 /opt/youarecoder/.env
```

### Step 3: Run Database Migration

```bash
# On production server
cd /opt/youarecoder
source venv/bin/activate

# Check pending migrations
flask db current

# Apply billing migration
flask db upgrade

# Verify migration success
flask db current
```

### Step 4: Restart Flask Application

```bash
# On production server
systemctl restart youarecoder

# Check service status
systemctl status youarecoder

# Verify no errors in logs
journalctl -u youarecoder -n 50 --no-pager
```

### Step 5: Verify Deployment

```bash
# Test billing endpoints
curl -I https://youarecoder.com/billing/
# Expected: 302 (redirect to login) or 200 (if authenticated)
# NOT: 404

# Test payment callback endpoint
curl -X POST https://youarecoder.com/billing/callback
# Expected: 400 (invalid hash) or 200
# NOT: 404

# Check Flask logs for blueprint registration
journalctl -u youarecoder | grep -i "billing"
```

---

## Quick Deployment Script

Save this as `/home/mustafa/youarecoder/deploy-billing-to-production.sh`:

```bash
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
```

---

## Manual Deployment (Alternative)

If the automated script fails, follow these manual steps:

### 1. Transfer Files Manually

```bash
# From local machine
cd /home/mustafa/youarecoder

# Create tarball of required files
tar -czf billing-deployment.tar.gz \
    app/__init__.py \
    app/routes/billing.py \
    app/services/paytr_service.py \
    app/services/email_service.py \
    app/templates/billing/ \
    app/templates/email/payment_*.html \
    app/templates/email/payment_*.txt \
    app/templates/email/trial_*.html \
    app/templates/email/trial_*.txt \
    migrations/versions/003_add_billing_models.py

# Transfer to production
sshpass -p 'tR$8vKz3&Pq9y#M2x7!hB5s' scp billing-deployment.tar.gz root@37.27.21.167:/tmp/

# SSH to production and extract
ssh root@37.27.21.167
cd /opt/youarecoder
tar -xzf /tmp/billing-deployment.tar.gz
rm /tmp/billing-deployment.tar.gz
```

### 2. Verify File Integrity

```bash
# On production server
cd /opt/youarecoder

# Check critical files exist
ls -lh app/routes/billing.py
ls -lh app/services/paytr_service.py
ls -lh app/templates/billing/
ls -lh migrations/versions/003_add_billing_models.py

# Verify billing blueprint import
grep -n "from app.routes import.*billing" app/__init__.py
grep -n "app.register_blueprint(billing.bp)" app/__init__.py
```

### 3. Apply Migration Manually

```bash
# On production server
cd /opt/youarecoder
source venv/bin/activate

# Check database state
flask db current

# Show pending migrations
flask db show

# Apply migration
flask db upgrade head

# Verify tables created
psql -U youarecoder_user -d youarecoder -c "\dt" | grep -E "(subscriptions|payments|invoices)"
```

### 4. Configure PayTR Environment

```bash
# Edit production environment file
nano /opt/youarecoder/.env

# Add these lines (replace with actual credentials):
PAYTR_MERCHANT_ID=TEST123
PAYTR_MERCHANT_KEY=TESTKEY123
PAYTR_MERCHANT_SALT=TESTSALT123
PAYTR_TEST_MODE=1
```

### 5. Restart Services

```bash
# Restart Flask app
systemctl restart youarecoder

# Check logs for errors
journalctl -u youarecoder -f
# Press Ctrl+C to stop watching

# Verify service is running
systemctl status youarecoder
```

---

## Validation Tests

After deployment, run these tests to verify billing system is working:

### Test 1: Billing Dashboard Accessibility

```bash
# Should redirect to login (302) or show billing page (200)
curl -I https://youarecoder.com/billing/
# Expected: HTTP/2 302 or HTTP/2 200
# NOT: HTTP/2 404
```

### Test 2: Payment Callback Endpoint

```bash
# Should reject invalid hash (400)
curl -X POST https://youarecoder.com/billing/callback \
    -d "merchant_oid=TEST123" \
    -d "status=success" \
    -d "hash=INVALID"
# Expected: 400 Bad Request
# NOT: 404 Not Found
```

### Test 3: Success Page

```bash
curl https://youarecoder.com/billing/payment/success
# Expected: HTML page with success message
# NOT: 404
```

### Test 4: Fail Page

```bash
curl https://youarecoder.com/billing/payment/fail
# Expected: HTML page with failure message
# NOT: 404
```

### Test 5: Database Tables

```bash
# On production server
psql -U youarecoder_user -d youarecoder -c "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('subscriptions', 'payments', 'invoices');"
# Expected: All 3 tables listed
```

---

## Rollback Procedure

If deployment fails, rollback with these steps:

```bash
# On production server
cd /opt/youarecoder

# Restore from git (if using git)
git checkout HEAD~1

# Rollback database migration
flask db downgrade -1

# Restart service
systemctl restart youarecoder
```

---

## Post-Deployment Tasks

### 1. Configure PayTR Live Credentials
Once PayTR store approval is received, update production:

```bash
# On production server
nano /opt/youarecoder/.env

# Update these values:
PAYTR_MERCHANT_ID=<live_merchant_id>
PAYTR_MERCHANT_KEY=<live_merchant_key>
PAYTR_MERCHANT_SALT=<live_merchant_salt>
PAYTR_TEST_MODE=0  # IMPORTANT: Set to 0 for live payments

# Restart to apply changes
systemctl restart youarecoder
```

### 2. Re-run E2E Tests

```bash
# From local machine
cd /home/mustafa/youarecoder
python tests/test_e2e_paytr_subscription.py

# Expected result: 6/7 or 7/7 tests passing
# (Login test may still fail due to field name, but billing tests should pass)
```

### 3. Monitor Production Logs

```bash
# Watch for billing-related activity
journalctl -u youarecoder -f | grep -i billing

# Watch for payment callbacks
journalctl -u youarecoder -f | grep -i paytr
```

### 4. Set Up Payment Monitoring

Add to admin dashboard or monitoring system:
- Payment success rate
- Failed payment alerts
- Webhook callback failures
- Subscription conversion metrics

---

## Troubleshooting

### Issue: Still getting 404 after deployment

**Diagnosis:**
```bash
# Check if billing blueprint is imported
grep -r "billing" /opt/youarecoder/app/__init__.py

# Check Flask startup logs
journalctl -u youarecoder -n 100 | grep -i blueprint
```

**Fix:**
- Verify `app/__init__.py` contains billing imports
- Check for syntax errors in billing.py
- Ensure venv has all dependencies: `pip install flask-mail`

### Issue: Database migration fails

**Diagnosis:**
```bash
# Check migration file exists
ls /opt/youarecoder/migrations/versions/003_add_billing_models.py

# Check database connection
flask shell
>>> from app import db
>>> db.engine
```

**Fix:**
- Verify PostgreSQL is running
- Check database credentials in config
- Manually create tables if migration fails

### Issue: PayTR callbacks return errors

**Diagnosis:**
```bash
# Check CSRF exemption
grep -A 5 "init_billing_csrf_exempt" /opt/youarecoder/app/__init__.py

# Test callback endpoint
curl -X POST https://youarecoder.com/billing/callback -v
```

**Fix:**
- Verify CSRF exemption is called in app factory
- Check PayTR credentials are configured
- Validate hash calculation logic

---

## Success Criteria

Deployment is successful when ALL of these are true:

- [ ] Billing routes return non-404 status codes
- [ ] Database migration applied (subscriptions/payments/invoices tables exist)
- [ ] PayTR environment variables configured
- [ ] E2E tests show billing system accessible
- [ ] No errors in Flask application logs
- [ ] Sample subscription can be initiated (test mode)

---

**Last Updated:** 2025-10-27
**Deployment Status:** Pending
**Deployment Owner:** DevOps / System Administrator
