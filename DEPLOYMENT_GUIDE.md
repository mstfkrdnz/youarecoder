# Dynamic Currency System - Deployment Guide

## Overview
This guide covers deploying the dynamic currency system with TCMB exchange rate integration.

## Pre-Deployment Checklist

### 1. Run Database Migration
```bash
cd /home/mustafa/youarecoder
source venv/bin/activate
FLASK_APP=app flask db upgrade
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade 008_add_workspace_metrics -> 009_exchange_rates, Add exchange rates table for dynamic currency conversion
```

### 2. Initial Rate Fetch
```bash
FLASK_APP=app flask update-exchange-rates
```

Expected output:
```
📊 Exchange Rate Update Summary:
  Effective Date: 2025-11-01
  Updated Currencies: USD, EUR
  Success: ✓

💱 Current Rates:
  USD/TRY: 34.2567 (as of 2025-11-01)
  EUR/TRY: 37.8912 (as of 2025-11-01)
  Total records: 2

✅ Exchange rates updated successfully.
```

### 3. Setup Cronjob Script
```bash
# Make script executable
chmod +x /home/mustafa/youarecoder/scripts/update-exchange-rates.sh

# Create log directory
sudo mkdir -p /var/log/youarecoder
sudo chown mustafa:mustafa /var/log/youarecoder

# Test the script
/home/mustafa/youarecoder/scripts/update-exchange-rates.sh

# Check log
tail -f /var/log/youarecoder/exchange-rates.log
```

### 4. Add Cronjob
```bash
crontab -e
```

Add these lines:
```cron
# Update TCMB exchange rates 3x daily at 16:00, 17:00, 18:00
0 16 * * * /home/mustafa/youarecoder/scripts/update-exchange-rates.sh
0 17 * * * /home/mustafa/youarecoder/scripts/update-exchange-rates.sh
0 18 * * * /home/mustafa/youarecoder/scripts/update-exchange-rates.sh
```

## Local Testing

### 1. Test Exchange Rate Fetching
```bash
cd /home/mustafa/youarecoder
source venv/bin/activate

# Test today's rates
FLASK_APP=app flask update-exchange-rates

# Test specific date
FLASK_APP=app flask update-exchange-rates --date 2025-10-31
```

### 2. Test Dynamic Pricing in Python Shell
```python
from config import Config
from app import create_app
from app.models import ExchangeRate

app = create_app()
with app.app_context():
    # Test get_plan_prices
    starter = Config.get_plan_prices('starter')
    print(f"Starter prices: {starter}")
    # Expected: {'TRY': 993, 'USD': 29, 'EUR': 26, 'rate_date': '2025-11-01'}

    team = Config.get_plan_prices('team')
    print(f"Team prices: {team}")
    # Expected: {'TRY': 3393, 'USD': 99, 'EUR': 90, 'rate_date': '2025-11-01'}

    # Test database query
    usd_rate = ExchangeRate.get_latest_rate('USD', 'TRY')
    print(f"Latest USD/TRY rate: {usd_rate.rate} (date: {usd_rate.effective_date})")
```

### 3. Test Billing Page
```bash
# Start local server
FLASK_APP=app FLASK_ENV=development flask run
```

Visit `http://localhost:5000/billing` and verify:
- ✅ USD is selected by default (not TRY)
- ✅ Exchange rate date shows: "💱 Exchange rates from 2025-11-01"
- ✅ Prices display correctly for all plans
- ✅ Currency switching works (TRY, USD, EUR)
- ✅ Prices match dynamic calculation

### 4. Test Payment Flow
1. Click "Select Starter Plan" with USD selected
2. Verify the payment request includes correct USD amount ($29)
3. Switch to TRY and try again
4. Verify TRY amount is calculated from exchange rate (~₺993)

## Production Deployment

### Server: root@37.27.21.167

### 1. Deploy Code Changes
```bash
ssh root@37.27.21.167 'cd /var/www/youarecoder && git pull && sudo systemctl restart youarecoder'
```

### 2. Run Migration on Production
```bash
ssh root@37.27.21.167 << 'EOF'
cd /var/www/youarecoder
source venv/bin/activate
FLASK_APP=app FLASK_ENV=production flask db upgrade
EOF
```

### 3. Fetch Initial Rates
```bash
ssh root@37.27.21.167 << 'EOF'
cd /var/www/youarecoder
source venv/bin/activate
FLASK_APP=app FLASK_ENV=production flask update-exchange-rates
EOF
```

### 4. Setup Cronjob on Production
```bash
ssh root@37.27.21.167 << 'EOF'
# Make script executable
chmod +x /var/www/youarecoder/scripts/update-exchange-rates.sh

# Create log directory
mkdir -p /var/log/youarecoder
chown youarecoder:youarecoder /var/log/youarecoder

# Add to root's crontab
(crontab -l 2>/dev/null; echo "0 16 * * * /var/www/youarecoder/scripts/update-exchange-rates.sh") | crontab -
(crontab -l 2>/dev/null; echo "0 17 * * * /var/www/youarecoder/scripts/update-exchange-rates.sh") | crontab -
(crontab -l 2>/dev/null; echo "0 18 * * * /var/www/youarecoder/scripts/update-exchange-rates.sh") | crontab -

# Verify crontab
crontab -l | grep exchange-rates
EOF
```

### 5. Verify Production Deployment
```bash
# Check database has exchange rates
ssh root@37.27.21.167 'sudo -u postgres psql -d youarecoder -c "SELECT * FROM exchange_rates ORDER BY effective_date DESC LIMIT 5;"'

# Check cronjob is active
ssh root@37.27.21.167 'crontab -l | grep exchange-rates'

# Monitor log file
ssh root@37.27.21.167 'tail -f /var/log/youarecoder/exchange-rates.log'
```

## Verification Checklist

### Database Verification
- [ ] Migration ran successfully (009_exchange_rates)
- [ ] exchange_rates table exists with correct schema
- [ ] Initial USD and EUR rates loaded
- [ ] Unique constraint works (no duplicate date/currency pairs)

### Rate Fetching Verification
- [ ] Manual CLI command works: `flask update-exchange-rates`
- [ ] Rates are saved to database correctly
- [ ] Fallback works when TCMB unavailable
- [ ] Historical date fetching works: `flask update-exchange-rates --date 2025-10-31`

### Cronjob Verification
- [ ] Script is executable
- [ ] Log directory exists with correct permissions
- [ ] Cronjob added to crontab (verify with `crontab -l`)
- [ ] Log file shows successful executions
- [ ] Rates update automatically at 16:00, 17:00, 18:00

### Frontend Verification
- [ ] Billing page loads without errors
- [ ] USD is default currency (not TRY)
- [ ] Exchange rate date displays correctly
- [ ] Starter plan shows $29 (USD), ~₺993 (TRY), ~€26 (EUR)
- [ ] Team plan shows $99 (USD), ~₺3393 (TRY), ~€90 (EUR)
- [ ] Enterprise plan shows $299 (USD), ~₺10,247 (TRY), ~€272 (EUR)
- [ ] Currency switching updates all plan prices
- [ ] Payment flow uses selected currency

### Error Handling Verification
- [ ] Fallback prices work when no rates in database
- [ ] Graceful degradation if TCMB API fails
- [ ] Error logging works correctly
- [ ] Retry logic works (test by blocking TCMB temporarily)

## Monitoring

### Daily Checks
```bash
# Check latest exchange rates
ssh root@37.27.21.167 'sudo -u postgres psql -d youarecoder -c "SELECT source_currency, rate, effective_date FROM exchange_rates ORDER BY effective_date DESC LIMIT 5;"'

# Check cronjob logs
ssh root@37.27.21.167 'tail -20 /var/log/youarecoder/exchange-rates.log'
```

### Weekly Checks
- Verify rates are updating daily
- Check for any failed cronjob executions
- Monitor log file size (rotate if needed)

## Troubleshooting

### Issue: No exchange rates in database
```bash
# Manually fetch rates
ssh root@37.27.21.167 'cd /var/www/youarecoder && source venv/bin/activate && FLASK_APP=app flask update-exchange-rates'

# Check for errors in log
ssh root@37.27.21.167 'tail -50 /var/log/youarecoder/exchange-rates.log'
```

### Issue: Cronjob not running
```bash
# Check crontab
ssh root@37.27.21.167 'crontab -l'

# Check cron service
ssh root@37.27.21.167 'systemctl status cron'

# Check script permissions
ssh root@37.27.21.167 'ls -la /var/www/youarecoder/scripts/update-exchange-rates.sh'
```

### Issue: TCMB API failing
```bash
# Test TCMB API directly
curl https://www.tcmb.gov.tr/kurlar/today.xml

# Check if it's a date issue (TCMB may not have weekend rates)
date  # If weekend, rates might not be available

# Manually fetch previous day's rate
ssh root@37.27.21.167 'cd /var/www/youarecoder && source venv/bin/activate && FLASK_APP=app flask update-exchange-rates --date 2025-10-31'
```

### Issue: Frontend not showing exchange rate date
```bash
# Check if dynamic_prices is being passed to template
ssh root@37.27.21.167 'grep -A 5 "dynamic_prices" /var/www/youarecoder/app/routes/billing.py'

# Check template syntax
ssh root@37.27.21.167 'grep -A 5 "rate_date" /var/www/youarecoder/app/templates/billing/dashboard.html'
```

## Rollback Plan

If issues occur, rollback with:
```bash
# 1. Revert code changes
ssh root@37.27.21.167 'cd /var/www/youarecoder && git reset --hard HEAD~1'

# 2. Downgrade migration
ssh root@37.27.21.167 'cd /var/www/youarecoder && source venv/bin/activate && FLASK_APP=app flask db downgrade'

# 3. Remove cronjob
ssh root@37.27.21.167 'crontab -l | grep -v exchange-rates | crontab -'

# 4. Restart service
ssh root@37.27.21.167 'sudo systemctl restart youarecoder'
```

## Success Criteria

✅ **Deployment is successful when:**
1. Migration completes without errors
2. Exchange rates fetch automatically 3x daily
3. Billing page defaults to USD
4. All three currencies display correct prices
5. Exchange rate date shows on billing page
6. Payment flow works with all currencies
7. Logs show successful rate updates
8. No errors in application logs

## Contact & Support

- **Logs Location**: `/var/log/youarecoder/exchange-rates.log`
- **Database**: PostgreSQL on root@37.27.21.167
- **Application**: `/var/www/youarecoder`
- **Service**: `sudo systemctl status youarecoder`
