# 🔴 Manual Payment Test Guide - Live Transaction

**CRITICAL**: This guide walks through testing the LIVE payment system with REAL money.

**Environment**: Production (https://youarecoder.com)
**Payment Mode**: 🔴 **LIVE** (PAYTR_TEST_MODE=0)
**Merchant ID**: 631116
**Test Amount**: $29 (Starter Plan - Minimum Risk)

---

## ⚠️ IMPORTANT WARNINGS

### Before You Begin

- 🔴 This will use **REAL CREDIT CARD** data
- 🔴 This will complete **REAL PAYMENT** transaction
- 🔴 **REAL MONEY** ($29) will be charged to your card
- 🔴 Transaction is **IRREVERSIBLE** (refund must be issued manually)

### Safety Measures
- ✅ Use your OWN credit card (verify immediately)
- ✅ Use SMALLEST plan ($29 Starter)
- ✅ Transaction is refundable via PayTR merchant panel
- ✅ Keep this as ONE-TIME test transaction

### Prerequisites
- ✅ PayTR live credentials configured (verified)
- ✅ Backend integration validated (safe validation test passed)
- ✅ Email service configured (Mailjet)
- ✅ Access to PayTR merchant panel (https://merchant.paytr.com)

---

## 📋 Pre-Test Checklist

### Step 1: Verify System Status
```bash
# SSH to production
ssh root@37.27.21.167

# Check service status
systemctl status youarecoder

# View recent logs (should be clean)
journalctl -u youarecoder -n 50 --no-pager

# Verify PayTR credentials
systemctl show youarecoder --property=Environment | grep PAYTR

# Expected output:
# PAYTR_MERCHANT_ID=631116
# PAYTR_TEST_MODE=0
# PAYTR_MERCHANT_KEY=[...]
# PAYTR_MERCHANT_SALT=[...]
```

### Step 2: Check Email Configuration
```bash
# Verify Mailjet configured
systemctl show youarecoder --property=Environment | grep MAIL

# Expected output:
# MAIL_SERVER=in-v3.mailjet.com
# MAIL_PORT=587
# MAIL_USERNAME=[...]
# MAIL_PASSWORD=[...]
# MAIL_DEFAULT_SENDER=noreply@youarecoder.com
# MAIL_SUPPRESS_SEND=False
```

### Step 3: Prepare Monitoring
Open these tabs in your browser BEFORE starting test:

1. **Production Site**: https://youarecoder.com
2. **PayTR Merchant Panel**: https://merchant.paytr.com (login required)
3. **Mailjet Dashboard**: https://app.mailjet.com/stats (login required)
4. **SSH Terminal**: Connected to production server with `journalctl -u youarecoder -f`

---

## 🧪 Test Execution Steps

### Phase 1: User Registration (5 minutes)

1. **Navigate to Registration**
   - URL: https://youarecoder.com
   - Click "Get Started" or navigate to /auth/register

2. **Fill Registration Form**
   ```
   Company Name: Test Payment Co
   Subdomain: testpayment[random]
   Admin Name: Test Admin
   Email: your-real-email@domain.com (use YOUR email!)
   Password: [secure password]
   ```

3. **Submit Registration**
   - Click "Register" button
   - Wait for redirect to dashboard
   - **Expected Result**: ✅ Registration success, redirected to dashboard

4. **Verify Trial Status**
   - Check dashboard for "14-day trial" message
   - Trial should be automatically assigned
   - **Expected Result**: ✅ Trial active, expiry date shown

### Phase 2: Billing Dashboard Access (2 minutes)

1. **Navigate to Billing**
   - URL: https://youarecoder.com/billing/
   - Or click "Billing" / "Manage Subscription" link

2. **Verify Dashboard Content**
   - Check for current trial status
   - Verify 3 plan options displayed (Starter, Team, Enterprise)
   - Confirm pricing shows correctly ($29, $99, $299)
   - **Expected Result**: ✅ Billing dashboard loads with all plans

3. **Review Plan Details**
   - Read Starter plan features
   - Confirm $29/month pricing
   - Note that you're about to subscribe to this plan
   - **Expected Result**: ✅ Plan details clear and correct

### Phase 3: Payment Initiation (🔴 CRITICAL - 5 minutes)

**⚠️ WARNING: Next steps will initiate REAL PAYMENT with REAL MONEY**

1. **Click Subscribe Button**
   - Click "Subscribe to Starter" button
   - **Expected Result**: ✅ Page loads (may show loading indicator)

2. **PayTR iframe Should Load**
   - **Expected Result**: ✅ PayTR payment form appears in iframe
   - iframe URL should contain: `paytr.com/odeme/guvenli/[TOKEN]`
   - Payment form should display:
     - Total amount: ₺870 (approx $29 * 30 TL/USD exchange rate)
     - Merchant name: YouAreCoder
     - Payment methods: Credit card, debit card

3. **Verify Payment Form Details**
   - Check amount is correct (₺870 or equivalent)
   - Verify merchant name is correct
   - Confirm payment gateway is PayTR
   - **Expected Result**: ✅ All details correct

### Phase 4: Payment Submission (🔴 REAL MONEY - 3 minutes)

**🚨 FINAL WARNING: This will charge REAL MONEY to your credit card!**

**Proceed only if:**
- ✅ You're ready to complete real transaction
- ✅ You're using YOUR OWN credit card
- ✅ Amount is correct ($29 / ₺870)
- ✅ You can refund this if needed

**Steps:**

1. **Enter Credit Card Details**
   ```
   Card Number: [16 digits]
   Expiry Date: MM/YY
   CVV: [3 digits]
   Cardholder Name: [your name]
   ```

2. **Submit Payment**
   - Click "Pay" / "Ödeme Yap" button
   - 3D Secure verification may appear (enter SMS code if prompted)
   - **Expected Result**: ✅ Payment processing starts

3. **Wait for Processing**
   - DO NOT close browser
   - DO NOT refresh page
   - Wait for redirect (may take 10-30 seconds)
   - **Expected Result**: ✅ Processing completes

### Phase 5: Payment Verification (10 minutes)

1. **Check Redirect**
   - **Expected**: Redirect to https://youarecoder.com/billing/payment/success
   - **Success Page Should Show**:
     - ✅ "Payment successful" message
     - ✅ Subscription activated
     - ✅ Thank you message

2. **Verify Application Logs** (SSH Terminal)
   ```bash
   # Watch logs in real-time
   journalctl -u youarecoder -f

   # Look for:
   # ✅ "Payment callback received" message
   # ✅ "Hash verification successful"
   # ✅ "Subscription activated"
   # ✅ "Email sent" confirmation
   # ❌ NO errors or exceptions
   ```

3. **Check Database Records**
   ```bash
   ssh root@37.27.21.167
   cd /root/youarecoder
   source venv/bin/activate

   python3 << 'EOF'
   from app import create_app, db
   from app.models import Payment, Subscription, Invoice

   app = create_app("production")
   with app.app_context():
       # Find latest payment
       payment = Payment.query.order_by(Payment.created_at.desc()).first()
       print(f"Latest Payment:")
       print(f"  ID: {payment.id}")
       print(f"  Amount: ${payment.amount / 100}")
       print(f"  Status: {payment.status}")
       print(f"  Merchant OID: {payment.merchant_oid}")

       # Find subscription
       subscription = Subscription.query.filter_by(company_id=payment.company_id).first()
       print(f"\nSubscription:")
       print(f"  Plan: {subscription.plan}")
       print(f"  Status: {subscription.status}")
       print(f"  Started: {subscription.started_at}")

       # Find invoice
       invoice = Invoice.query.filter_by(payment_id=payment.id).first()
       if invoice:
           print(f"\nInvoice:")
           print(f"  Number: {invoice.invoice_number}")
           print(f"  Amount: ${invoice.amount / 100}")
   EOF
   ```

   **Expected Output**:
   ```
   Latest Payment:
     ID: 1
     Amount: $29.0
     Status: completed
     Merchant OID: YAC-[timestamp]-[random]

   Subscription:
     Plan: starter
     Status: active
     Started: 2025-10-28 07:00:00

   Invoice:
     Number: INV-2025-00001
     Amount: $29.0
   ```

4. **Check Email Notification**
   - Open your email inbox (email used during registration)
   - Look for email from: noreply@youarecoder.com
   - Subject should be: "Payment Successful - YouAreCoder"
   - **Expected Email Content**:
     - ✅ Payment confirmation
     - ✅ Amount: $29
     - ✅ Plan: Starter
     - ✅ Invoice number
     - ✅ Subscription details

5. **Verify PayTR Merchant Panel**
   - Login to: https://merchant.paytr.com
   - Navigate to "Transactions" / "İşlemler"
   - Look for latest transaction
   - **Expected Transaction**:
     - ✅ Amount: ₺870 (or equivalent)
     - ✅ Status: Success / Başarılı
     - ✅ Merchant OID matches database
     - ✅ Customer email matches

6. **Check Mailjet Dashboard**
   - Login to: https://app.mailjet.com/stats
   - Check "Messages" / "Sent" section
   - Look for recent email
   - **Expected**:
     - ✅ Email sent successfully
     - ✅ Recipient: your test email
     - ✅ Status: Delivered
     - ✅ No bounces or errors

---

## ✅ Success Criteria

### All Must Pass

- ✅ Payment processed successfully through PayTR
- ✅ User redirected to success page
- ✅ Database records created:
  - Payment record (status: completed)
  - Subscription record (status: active, plan: starter)
  - Invoice record generated
- ✅ Email notification sent and delivered
- ✅ PayTR merchant panel shows transaction
- ✅ No errors in application logs
- ✅ Billing dashboard shows active subscription

### If ANY Fail

- ❌ DO NOT proceed with marketing launch
- ❌ Review application logs for errors
- ❌ Check PayTR merchant panel for transaction status
- ❌ Verify email configuration
- ❌ Contact PayTR support if payment issues
- ❌ Issue refund via PayTR merchant panel if needed

---

## 🔧 Troubleshooting

### Issue 1: Payment Form Doesn't Load

**Symptoms**: PayTR iframe doesn't appear or shows error

**Diagnosis**:
```bash
# Check logs for token generation
journalctl -u youarecoder -n 100 | grep -i "token\|paytr"

# Look for:
# - "Token generation successful"
# - OR "PayTR API error"
```

**Solutions**:
1. Verify PayTR credentials in systemd service
2. Check PayTR API status: https://www.paytr.com/durumdurum
3. Review PayTR merchant panel for any account issues

### Issue 2: Payment Fails / Rejects

**Symptoms**: Payment form shows error after card submission

**Diagnosis**:
```bash
# Check logs for callback
journalctl -u youarecoder -n 100 | grep -i "callback"

# Look for:
# - "Payment callback received"
# - "Hash verification failed" (security issue)
# - "Payment failed" (PayTR rejected)
```

**Solutions**:
1. Verify credit card has sufficient funds
2. Check if 3D Secure is required and was completed
3. Review PayTR merchant panel for rejection reason
4. Try different credit card if persistent issues

### Issue 3: Email Not Received

**Symptoms**: Payment successful but no email

**Diagnosis**:
```bash
# Check logs for email sending
journalctl -u youarecoder -n 100 | grep -i "email\|mail"

# Look for:
# - "Email sent successfully"
# - OR "Email sending failed"
```

**Solutions**:
1. Check spam/junk folder
2. Verify Mailjet dashboard for send status
3. Check Mailjet account status and quota
4. Verify email configuration in systemd service

### Issue 4: Callback Hash Verification Fails

**Symptoms**: Payment appears successful but subscription not activated

**Diagnosis**:
```bash
# Check logs for hash verification
journalctl -u youarecoder -n 100 | grep -i "hash"

# Look for:
# - "Hash verification failed"
# - "Invalid hash"
```

**Solutions**:
1. Verify PayTR credentials are correct (MERCHANT_KEY, MERCHANT_SALT)
2. Check PAYTR_TEST_MODE=0 in systemd service
3. Review PayTR callback data in logs
4. Contact PayTR support if credentials might be wrong

---

## 💰 Post-Test Actions

### If Test PASSED ✅

1. **Document Results**
   - Save all logs and screenshots
   - Record transaction ID from PayTR
   - Note any issues encountered

2. **Optional: Issue Refund**
   ```
   If you want to refund the $29 test transaction:

   1. Login to PayTR merchant panel
   2. Navigate to transaction
   3. Click "Refund" / "İade"
   4. Select full refund amount
   5. Submit refund request
   6. Refund typically processes within 2-7 days
   ```

3. **Update Master Plan**
   - Mark "Live Payment Testing" as complete
   - Update production readiness status to 100%

4. **Marketing Launch Preparation**
   - System is ready for customer payments ✅
   - Monitor first 24-48 hours closely
   - Provide customer support channels

### If Test FAILED ❌

1. **DO NOT Launch Marketing**
   - Fix identified issues first
   - Re-run validation tests
   - Perform another manual payment test

2. **Issue Refund Immediately**
   - Login to PayTR merchant panel
   - Refund the failed transaction
   - Document what went wrong

3. **Debug & Fix**
   - Review all error logs
   - Fix configuration issues
   - Re-deploy if necessary
   - Run safe validation test again

4. **Re-Test**
   - After fixes, repeat manual payment test
   - Only proceed to launch when test passes

---

## 📊 Test Report Template

After completing the manual test, fill out this template:

```markdown
# Manual Payment Test Report

**Test Date**: 2025-10-28 [TIME] UTC
**Tester**: [Your Name]
**Environment**: Production (https://youarecoder.com)

## Test Results

### Payment Processing
- [ ] PayTR iframe loaded successfully
- [ ] Payment form displayed correct amount
- [ ] Credit card accepted
- [ ] 3D Secure completed (if applicable)
- [ ] Payment processed successfully

### Backend Integration
- [ ] Callback received
- [ ] Hash verification passed
- [ ] Database records created (payment, subscription, invoice)
- [ ] No errors in application logs

### User Experience
- [ ] Redirected to success page
- [ ] Success message displayed correctly
- [ ] Billing dashboard shows active subscription

### Notifications
- [ ] Email notification sent
- [ ] Email delivered successfully
- [ ] Email content correct

### PayTR Merchant Panel
- [ ] Transaction visible in panel
- [ ] Transaction status: Success
- [ ] Amount correct
- [ ] Merchant OID matches database

## Issues Encountered
[Describe any problems]

## Overall Result
- [ ] ✅ PASS - Ready for production
- [ ] ❌ FAIL - Requires fixes

## Next Steps
[List any actions needed]

## Screenshots
[Attach key screenshots]
```

---

## 🎯 Success Confirmation

**After manual test passes, you can confidently state:**

✅ PayTR live payment integration is FULLY OPERATIONAL
✅ Backend processes payments correctly
✅ Database updates work as expected
✅ Email notifications are delivered
✅ PayTR merchant integration is complete
✅ **READY FOR CUSTOMER PAYMENTS** 🚀

---

## 📞 Support Contacts

### PayTR Support
- **Website**: https://www.paytr.com
- **Merchant Panel**: https://merchant.paytr.com
- **Support Email**: destek@paytr.com
- **Phone**: (TR) +90 850 532 78 97

### Mailjet Support
- **Dashboard**: https://app.mailjet.com
- **Documentation**: https://dev.mailjet.com
- **Support Email**: support@mailjet.com

### Application Support
- **Production Server**: root@37.27.21.167
- **Logs**: `journalctl -u youarecoder -f`
- **Service Control**: `systemctl status/restart youarecoder`

---

**Test Guide Version**: 1.0
**Created**: 2025-10-28
**Author**: Claude (QA Specialist)
**Environment**: Production (LIVE)
**Status**: Ready for Execution
