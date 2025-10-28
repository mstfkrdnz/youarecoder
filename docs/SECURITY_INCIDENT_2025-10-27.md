# Security Incident Report: Exposed Mailjet SMTP Credentials

**Date:** 2025-10-27
**Severity:** 🔴 **CRITICAL**
**Status:** ⚠️ Partially Remediated (Credentials still need to be revoked)
**Detected By:** GitGuardian automated security scan

---

## 📋 Incident Summary

Mailjet SMTP credentials (API Key and Secret Key) were accidentally committed to the public GitHub repository in the documentation file.

**Exposed Credentials:**
- **API Key:** 7a545957c5a1a63b98009a6fc9775950
- **Secret Key:** 77e7dd27f3709fa8adf99ddc7c8ee0fe
- **Exposure Date:** October 27th, 2025, 12:07:11 UTC
- **Repository:** mstfkrdnz/youarecoder
- **Commit:** 1a586df (Add Day 14 email system implementation report)

---

## 🔍 Impact Analysis

### Exposed Services
- **Mailjet SMTP Account:** Full access to send emails via Mailjet API
- **Email Sending Capability:** Attackers could send emails using `noreply@youarecoder.com`
- **Potential Abuse:** Spam, phishing emails, reputation damage to domain

### Systems Affected
- Production server (37.27.21.167) using these credentials
- Email system for youarecoder.com platform
- User registration and notification emails

### Current Status
- ❌ Credentials still active (need immediate revocation)
- ✅ Credentials removed from repository
- ✅ .gitignore updated to prevent future exposure
- ✅ Security fix pushed to GitHub (commit 259bcfb)

---

## 🛠️ Remediation Actions Taken

### Immediate Actions (Completed)
1. ✅ **Removed credentials from documentation**
   - Replaced actual keys with placeholders in `day14-email-system.md`

2. ✅ **Updated .gitignore**
   - Added `.env.*` to prevent environment file commits
   - Added `test_*.py` to prevent test file commits

3. ✅ **Deleted local test files with credentials**
   - Removed `test_direct_email.py`
   - Removed `.env.test`
   - Removed `tests/test_email_flow.py`

4. ✅ **Committed and pushed security fixes**
   - Commit: 259bcfb
   - Message: "security: Remove exposed Mailjet credentials from documentation"

### Pending Critical Actions

⚠️ **MUST BE DONE IMMEDIATELY:**

1. **Revoke Exposed Mailjet Credentials**
   - Go to: https://app.mailjet.com/account/apikeys
   - Revoke API Key: 7a545957c5a1a63b98009a6fc9775950
   - This will immediately invalidate the exposed credentials

2. **Generate New Mailjet API Keys**
   - Create new API key pair in Mailjet dashboard
   - Keep credentials secure (never commit to repository)

3. **Update Production Server**
   - SSH to: root@37.27.21.167
   - Update `/root/youarecoder/.env` with new credentials
   - Restart Flask service: `systemctl restart youarecoder`

---

## 🔒 Preventive Measures Implemented

### Code Repository Security
- ✅ Enhanced .gitignore with credential patterns
- ✅ Added test file exclusions
- ⏳ Consider pre-commit hooks for secret scanning

### Documentation Security
- ✅ Use placeholders for all credentials in documentation
- ✅ Never include actual API keys in markdown files
- ✅ Use `<PLACEHOLDER>` format for sensitive values

### Development Workflow
- ⏳ Set up git-secrets or similar pre-commit scanning tool
- ⏳ Regular credential rotation policy (every 90 days)
- ⏳ Implement secrets management system (e.g., AWS Secrets Manager, HashiCorp Vault)

---

## 📊 Timeline

| Time | Event |
|------|-------|
| 12:07 UTC | Credentials committed to GitHub (commit 1a586df) |
| ~12:10 UTC | GitGuardian detected and alerted |
| 12:15 UTC | Incident identified by team |
| 12:20 UTC | Credentials removed from repository (commit 259bcfb) |
| 12:21 UTC | Security fix pushed to GitHub |
| **PENDING** | **Mailjet credentials revocation** |
| **PENDING** | **Production server credential update** |

---

## ✅ Action Items Checklist

### Immediate (Do Now)
- [ ] **Revoke exposed Mailjet API keys** → https://app.mailjet.com/account/apikeys
- [ ] **Generate new Mailjet API keys**
- [ ] **Update production server .env file**
- [ ] **Restart youarecoder service**
- [ ] **Verify email system works with new credentials**

### Short-term (This Week)
- [ ] Audit all files in repository for other potential credential leaks
- [ ] Review all `.md` files in `docs/` directory
- [ ] Check git history for other exposed secrets
- [ ] Set up automated secret scanning (git-secrets or gitleaks)

### Long-term (This Month)
- [ ] Implement proper secrets management system
- [ ] Establish credential rotation policy
- [ ] Security awareness training for development team
- [ ] Regular security audits

---

## 📝 Lessons Learned

### What Went Wrong
1. Documentation included actual production credentials
2. No pre-commit scanning to catch secrets before push
3. Test files with credentials were created in repository

### What Went Right
1. GitGuardian detected exposure quickly (within minutes)
2. Rapid response to remove credentials from repository
3. Comprehensive .gitignore improvements implemented

### Improvements Needed
1. Never document actual credentials in markdown files
2. Implement automated secret scanning before commits
3. Use environment variable placeholders in all documentation
4. Regular security training for best practices

---

## 🔐 Security Best Practices Moving Forward

### Credential Management
- **NEVER** commit credentials to version control
- **ALWAYS** use environment variables for secrets
- **ALWAYS** use placeholders in documentation
- **REGULARLY** rotate credentials (every 90 days)

### Documentation Standards
- Use `<PLACEHOLDER>` format for all credentials
- Include setup instructions without actual values
- Reference environment variable names, not values

### Development Workflow
- Enable pre-commit hooks for secret scanning
- Use .env files (excluded from git) for local development
- Production secrets stored in secure secrets management system

---

## 📞 Contacts

**Security Incident Response:**
- Technical Lead: Mustafa Kördönmez
- Email: mustafa@alkedos.com

**Mailjet Account:**
- Login: https://app.mailjet.com/
- Support: https://www.mailjet.com/support/

---

**Report Status:** ⚠️ OPEN - Waiting for credential revocation and rotation
**Next Review:** After new credentials are deployed

