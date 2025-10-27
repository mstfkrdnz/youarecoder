# PayTR Billing - Production Deployment Guide

## Quick Start

This guide covers deploying the PayTR billing integration to production.

---

## Step 1: PayTR Account Setup

### 1.1 Get PayTR Merchant Credentials
1. Login to PayTR merchant dashboard: https://merchant.paytr.com
2. Navigate to **Settings → API Credentials**
3. Copy these values:
   - Merchant ID
   - Merchant Key
   - Merchant Salt

### 1.2 Configure Callback URLs
In PayTR merchant dashboard:
1. Go to **Settings → Callback URLs**
2. Set callback URL: `https://youarecoder.com/billing/callback`
3. Set success URL: `https://youarecoder.com/billing/payment/success`
4. Set failure URL: `https://youarecoder.com/billing/payment/fail`

---

## Step 2: Environment Configuration

### 2.1 Staging Environment (Test Mode)
```bash
# .env.staging
PAYTR_MERCHANT_ID=your_test_merchant_id
PAYTR_MERCHANT_KEY=your_test_merchant_key
PAYTR_MERCHANT_SALT=your_test_merchant_salt
PAYTR_TEST_MODE=1  # Test mode enabled
PAYTR_TIMEOUT_LIMIT=30
BASE_URL=https://staging.youarecoder.com
```

### 2.2 Production Environment
```bash
# .env.production
PAYTR_MERCHANT_ID=your_production_merchant_id
PAYTR_MERCHANT_KEY=your_production_merchant_key
PAYTR_MERCHANT_SALT=your_production_merchant_salt
PAYTR_TEST_MODE=0  # Live payments
PAYTR_TIMEOUT_LIMIT=30
BASE_URL=https://youarecoder.com
```

**⚠️ Security**: Never commit `.env` files to git!

---

## Step 3: Database Migration

### 3.1 Backup Current Database
```bash
# SSH to server
ssh root@37.27.21.167

# Backup database
pg_dump -U youarecoder_user -d youarecoder > /tmp/backup_before_billing_$(date +%Y%m%d).sql
```

### 3.2 Run Migration
```bash
# Activate virtual environment
source /opt/youarecoder/venv/bin/activate

# Navigate to project
cd /opt/youarecoder

# Run migration
flask db upgrade

# Verify tables created
psql -U youarecoder_user -d youarecoder -c "\dt"
# Should show: subscriptions, payments, invoices tables
```

### 3.3 Verify Migration
```bash
# Check table structure
psql -U youarecoder_user -d youarecoder -c "\d subscriptions"
psql -U youarecoder_user -d youarecoder -c "\d payments"
psql -U youarecoder_user -d youarecoder -c "\d invoices"
```

---

## Step 4: Application Deployment

### 4.1 Update Application Code
```bash
# On server
cd /opt/youarecoder
git pull origin main

# Install dependencies (if any new)
source venv/bin/activate
pip install -r requirements.txt
```

### 4.2 Set Environment Variables
```bash
# Edit environment file
nano /opt/youarecoder/.env

# Add PayTR configuration (see Step 2.2)
# Save and exit (Ctrl+X, Y, Enter)
```

### 4.3 Restart Application
```bash
# Restart Flask application (systemd service)
sudo systemctl restart youarecoder

# Check status
sudo systemctl status youarecoder

# Check logs
sudo journalctl -u youarecoder -f
```

---

## Step 5: Staging Testing

### 5.1 Test Payment Flow
1. Navigate to staging: `https://staging.youarecoder.com/pricing`
2. Click "Subscribe" on any plan
3. Verify iframe opens with PayTR test payment page
4. Complete test payment using PayTR test card:
   - **Card Number**: 4508 0345 0803 4509
   - **Expiry**: 12/26
   - **CVV**: 000
5. Verify redirect to success page
6. Check billing dashboard: `/billing/`
7. Verify subscription status changed to "active"

### 5.2 Test Callback Processing
```bash
# Check application logs for callback
sudo journalctl -u youarecoder -f | grep "payment callback"

# Verify payment record in database
psql -U youarecoder_user -d youarecoder -c "SELECT * FROM payments ORDER BY created_at DESC LIMIT 1;"

# Verify subscription activated
psql -U youarecoder_user -d youarecoder -c "SELECT * FROM subscriptions ORDER BY created_at DESC LIMIT 1;"
```

### 5.3 Test Error Scenarios
1. **Invalid Plan**: Try `/billing/subscribe/invalid` → Should return 400
2. **Unauthenticated**: Logout, try to subscribe → Should redirect to login
3. **Invalid Hash**: Manually POST to callback with wrong hash → Should return 400

---

## Step 6: Production Deployment

### 6.1 Pre-Deployment Checklist
- [ ] Staging tests passed
- [ ] Database backup completed
- [ ] PayTR production credentials configured
- [ ] `PAYTR_TEST_MODE=0` set
- [ ] SSL certificate valid (HTTPS required)
- [ ] Monitoring/alerting configured

### 6.2 Deploy to Production
```bash
# SSH to production server
ssh root@37.27.21.167

# Switch to production environment
export FLASK_ENV=production

# Update code
cd /opt/youarecoder
git pull origin main

# Set production environment variables
nano /opt/youarecoder/.env
# Set PAYTR_TEST_MODE=0
# Set BASE_URL=https://youarecoder.com

# Restart application
sudo systemctl restart youarecoder

# Monitor logs
sudo journalctl -u youarecoder -f
```

### 6.3 Production Smoke Test
1. Make small test purchase (Starter plan: $29)
2. Verify complete payment flow
3. Check subscription activated
4. Verify invoice generated
5. Test billing dashboard access

---

## Step 7: Monitoring & Alerting

### 7.1 Log Monitoring
```bash
# Watch for payment errors
sudo journalctl -u youarecoder -f | grep -i "error\|payment"

# Monitor callback processing
sudo journalctl -u youarecoder -f | grep "callback"
```

### 7.2 Database Monitoring
```sql
-- Check recent payments
SELECT
    p.id,
    p.paytr_merchant_oid,
    p.amount / 100.0 as amount_usd,
    p.status,
    p.created_at,
    c.name as company_name
FROM payments p
JOIN companies c ON p.company_id = c.id
ORDER BY p.created_at DESC
LIMIT 10;

-- Check active subscriptions
SELECT
    s.id,
    c.name as company_name,
    s.plan,
    s.status,
    s.trial_ends_at,
    s.current_period_end
FROM subscriptions s
JOIN companies c ON s.company_id = c.id
WHERE s.status IN ('trial', 'active')
ORDER BY s.created_at DESC;

-- Check failed payments
SELECT
    p.paytr_merchant_oid,
    p.failure_reason_code,
    p.failure_reason_message,
    p.created_at
FROM payments
WHERE status = 'failed'
ORDER BY created_at DESC
LIMIT 10;
```

### 7.3 Alerts to Configure
- Payment callback failures (HTTP 4xx/5xx)
- Subscription activation failures
- Invalid hash attempts (potential fraud)
- PayTR API timeout/errors
- Database connection issues

---

## Step 8: Trial Period Management

### 8.1 Trial Expiration Monitoring
```sql
-- Find trials expiring in next 7 days
SELECT
    c.name,
    c.subdomain,
    s.plan,
    s.trial_ends_at,
    EXTRACT(DAY FROM (s.trial_ends_at - NOW())) as days_remaining
FROM subscriptions s
JOIN companies c ON s.company_id = c.id
WHERE s.status = 'trial'
AND s.trial_ends_at BETWEEN NOW() AND NOW() + INTERVAL '7 days'
ORDER BY s.trial_ends_at;
```

### 8.2 Trial Expiration Cron Job (TODO)
```bash
# Create cron job to check trial expirations
# Add to crontab: crontab -e

# Run daily at 9 AM
0 9 * * * /opt/youarecoder/scripts/check_trial_expirations.sh

# Script should:
# 1. Find trials expiring in 7 days
# 2. Send email reminder
# 3. Find expired trials
# 4. Disable workspace access
```

---

## Troubleshooting

### Issue: Invalid Hash Error
**Symptom**: Callback returns "Invalid hash"
**Cause**: Merchant key/salt mismatch
**Solution**:
```bash
# Verify credentials match PayTR dashboard
echo $PAYTR_MERCHANT_KEY
echo $PAYTR_MERCHANT_SALT

# Check hash generation in logs
sudo journalctl -u youarecoder -f | grep "hash"
```

### Issue: Payment Success but Subscription Not Activated
**Symptom**: Payment status "success" but subscription still "trial"
**Cause**: Callback processing error
**Solution**:
```sql
-- Check payment and subscription status
SELECT
    p.id,
    p.status as payment_status,
    s.status as subscription_status,
    p.paytr_merchant_oid
FROM payments p
LEFT JOIN subscriptions s ON p.subscription_id = s.id
WHERE p.paytr_merchant_oid = 'YAC-XXX-XXX';

-- Check application logs for callback errors
sudo journalctl -u youarecoder | grep "process_payment_callback"
```

### Issue: CSRF Token Missing on Callback
**Symptom**: PayTR callback returns 400 CSRF error
**Cause**: `init_billing_csrf_exempt()` not called
**Solution**:
```python
# Verify in app/__init__.py:
from app.routes import billing
billing.init_billing_csrf_exempt(csrf)
```

### Issue: PayTR iframe Not Loading
**Symptom**: Blank page or error when opening payment iframe
**Cause**: Invalid merchant credentials or incorrect hash
**Solution**:
```bash
# Check logs for token generation errors
sudo journalctl -u youarecoder -f | grep "generate_iframe_token"

# Test with PayTR test credentials first (PAYTR_TEST_MODE=1)
```

---

## Rollback Plan

### If Critical Issues Occur
```bash
# 1. Restore database backup
psql -U youarecoder_user -d youarecoder < /tmp/backup_before_billing_YYYYMMDD.sql

# 2. Rollback code
cd /opt/youarecoder
git checkout HEAD~1  # Revert to previous commit

# 3. Restart application
sudo systemctl restart youarecoder

# 4. Verify application works
curl -I https://youarecoder.com/health
```

---

## Post-Deployment Verification

### Checklist
- [ ] Test payment flow completed successfully
- [ ] Callback endpoint receiving PayTR notifications
- [ ] Subscriptions activating correctly
- [ ] Invoices generating properly
- [ ] Billing dashboard loading
- [ ] No errors in application logs
- [ ] Database queries performing well
- [ ] SSL certificate valid
- [ ] PayTR webhook URL configured

### Success Criteria
✅ First successful live payment processed
✅ Subscription activated automatically
✅ Invoice generated and stored
✅ User can access billing dashboard
✅ No critical errors in logs

---

## Support & Maintenance

### PayTR Support
- Technical Support: https://support.paytr.com
- Documentation: https://dev.paytr.com
- Merchant Dashboard: https://merchant.paytr.com

### Internal Documentation
- Implementation Summary: [claudedocs/billing_implementation_summary.md](claudedocs/billing_implementation_summary.md)
- Service Code: [app/services/paytr_service.py](app/services/paytr_service.py)
- Route Code: [app/routes/billing.py](app/routes/billing.py)
- Test Suite: [tests/test_billing_routes.py](tests/test_billing_routes.py)

### Monitoring Dashboards
- Application Logs: `sudo journalctl -u youarecoder -f`
- Database Queries: See "Database Monitoring" section above
- PayTR Dashboard: https://merchant.paytr.com/reports

---

## Next Steps (Post-Deployment)

1. **Email Notifications** (High Priority)
   - Payment success/failure emails
   - Trial expiration reminders
   - Invoice delivery
   - See: TODO in `paytr_service.py:115-120`

2. **Invoice PDF Generation** (Medium Priority)
   - Generate PDF invoices
   - Email to customers
   - Admin download feature

3. **Admin Dashboard** (Medium Priority)
   - View all subscriptions
   - Manual activation/cancellation
   - Refund processing
   - Revenue reports

4. **Webhook Retry Logic** (Low Priority)
   - Implement idempotency
   - Retry failed webhooks
   - Comprehensive logging

---

**Document Version**: 1.0
**Last Updated**: 2025-10-27
**Author**: Claude Code (PayTR Integration Team)
