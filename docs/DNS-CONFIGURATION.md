# DNS Configuration Guide - YouAreCoder.com

## 📋 Overview

This guide provides complete DNS configuration for the YouAreCoder.com multi-tenant SaaS platform.

**Platform Architecture:**
- Main domain serves landing page and company registration
- Company subdomains serve admin dashboards
- Workspace subdomains serve code-server instances
- Wildcard SSL certificate covers all subdomains

---

## 🎯 DNS Requirements

### Required DNS Records

| Type | Name | Value | TTL | Purpose |
|------|------|-------|-----|---------|
| A | @ | 46.62.150.235 | 300 | Main domain (youarecoder.com) |
| A | * | 46.62.150.235 | 300 | Wildcard for all subdomains |
| AAAA | @ | [IPv6 if available] | 300 | IPv6 support (optional) |
| AAAA | * | [IPv6 if available] | 300 | IPv6 wildcard (optional) |

### Optional DNS Records (Recommended)

| Type | Name | Value | TTL | Purpose |
|------|------|-------|-----|---------|
| MX | @ | mail.youarecoder.com | 3600 | Email routing |
| TXT | @ | "v=spf1 include:_spf.mx.cloudflare.net ~all" | 3600 | SPF record |
| CNAME | www | youarecoder.com | 300 | WWW redirect |

---

## 🚀 Quick Setup (5 Minutes)

### Step 1: Access Your Domain Provider
Login to your domain registrar (e.g., GoDaddy, Namecheap, Cloudflare)

### Step 2: Navigate to DNS Management
Find "DNS Management", "DNS Settings", or "Advanced DNS"

### Step 3: Add A Record for Root Domain
```
Type: A
Name: @ (or leave empty)
Value: 46.62.150.235
TTL: 300 (5 minutes)
```

### Step 4: Add Wildcard A Record
```
Type: A
Name: *
Value: 46.62.150.235
TTL: 300 (5 minutes)
```

### Step 5: Save and Verify
Click "Save" or "Apply Changes"

---

## 🔍 DNS Verification

### Verify DNS Propagation

**Check root domain:**
```bash
dig youarecoder.com +short
# Expected output: 46.62.150.235
```

**Check wildcard subdomain:**
```bash
dig testco.youarecoder.com +short
# Expected output: 46.62.150.235

dig dev-acme.youarecoder.com +short
# Expected output: 46.62.150.235
```

**Check from multiple locations:**
```bash
# Use online tools:
# - https://dnschecker.org
# - https://www.whatsmydns.net
```

### DNS Propagation Timeline

| Status | Time | Availability |
|--------|------|--------------|
| Local DNS | 0-5 min | Your ISP only |
| Regional | 5-30 min | Your country |
| Global | 30 min - 24 hours | Worldwide |

**Recommendation:** Wait 1-2 hours before SSL certificate generation for stable DNS.

---

## 🔐 SSL Certificate Setup (Let's Encrypt)

Once DNS is propagated, Traefik will automatically generate SSL certificates.

### Automatic Certificate Generation

**Traefik Configuration (already set):**
```yaml
certificatesResolvers:
  letsencrypt:
    acme:
      email: admin@youarecoder.com
      storage: /etc/traefik/acme.json
      httpChallenge:
        entryPoint: web
```

### Wildcard Certificate (Manual - Optional)

For wildcard certificate, DNS-01 challenge is required:

**Step 1: Generate certificate request**
```bash
certbot certonly --manual --preferred-challenges dns \
  -d youarecoder.com -d *.youarecoder.com \
  --email admin@youarecoder.com
```

**Step 2: Add TXT records**
Certbot will provide TXT records like:
```
Type: TXT
Name: _acme-challenge.youarecoder.com
Value: [provided by certbot]
TTL: 300
```

**Step 3: Verify and complete**
```bash
# Check TXT record
dig _acme-challenge.youarecoder.com TXT +short

# Press Enter in certbot to complete
```

---

## 🌐 Subdomain Structure

### Domain Hierarchy

```
youarecoder.com (A: 46.62.150.235)
├── Landing page & registration
│
*.youarecoder.com (A: 46.62.150.235)
├── Company dashboards:
│   ├── testco.youarecoder.com
│   ├── acmecorp.youarecoder.com
│   └── startup123.youarecoder.com
│
└── Workspace code-servers:
    ├── dev-testco.youarecoder.com
    ├── john-acmecorp.youarecoder.com
    └── staging-startup123.youarecoder.com
```

### Routing Logic (Traefik)

**Main Flask App:**
- `youarecoder.com` → Flask (landing, register)
- `{company}.youarecoder.com` → Flask (company dashboard)

**Code-Server Workspaces:**
- `{workspace}-{company}.youarecoder.com` → code-server on port 800X

---

## 📊 Provider-Specific Guides

### Cloudflare

1. Login to Cloudflare Dashboard
2. Select your domain
3. Go to **DNS** tab
4. Click **Add record**
5. Add A record for `@`:
   - Type: `A`
   - Name: `@`
   - IPv4: `46.62.150.235`
   - Proxy status: `DNS only` (gray cloud)
   - TTL: `Auto`
6. Click **Add record** again
7. Add A record for wildcard:
   - Type: `A`
   - Name: `*`
   - IPv4: `46.62.150.235`
   - Proxy status: `DNS only` (gray cloud)
   - TTL: `Auto`
8. Click **Save**

**Important:** Set proxy status to "DNS only" (gray cloud), not "Proxied" (orange cloud), to allow Let's Encrypt validation.

### Namecheap

1. Login to Namecheap account
2. Go to **Domain List**
3. Click **Manage** next to your domain
4. Go to **Advanced DNS** tab
5. Click **Add New Record**
6. Add A record:
   - Type: `A Record`
   - Host: `@`
   - Value: `46.62.150.235`
   - TTL: `5 min`
7. Add wildcard A record:
   - Type: `A Record`
   - Host: `*`
   - Value: `46.62.150.235`
   - TTL: `5 min`
8. Click **Save All Changes**

### GoDaddy

1. Login to GoDaddy account
2. Go to **My Products**
3. Find your domain and click **DNS**
4. Click **Add** under Records
5. Add A record:
   - Type: `A`
   - Name: `@`
   - Value: `46.62.150.235`
   - TTL: `Custom - 300 seconds`
6. Click **Add** again
7. Add wildcard A record:
   - Type: `A`
   - Name: `*`
   - Value: `46.62.150.235`
   - TTL: `Custom - 300 seconds`
8. Click **Save**

---

## 🧪 Testing After DNS Setup

### 1. DNS Resolution Test
```bash
# Check DNS propagation
for subdomain in "" "testco" "dev-acme" "john-startup"; do
  if [ -z "$subdomain" ]; then
    echo "Testing: youarecoder.com"
    dig youarecoder.com +short
  else
    echo "Testing: ${subdomain}.youarecoder.com"
    dig ${subdomain}.youarecoder.com +short
  fi
done
```

Expected output: All should return `46.62.150.235`

### 2. HTTP Connection Test
```bash
# Test HTTP (should redirect to HTTPS)
curl -I http://youarecoder.com

# Expected: HTTP/1.1 308 Permanent Redirect
# Location: https://youarecoder.com
```

### 3. HTTPS Connection Test (after SSL setup)
```bash
# Test HTTPS
curl -I https://youarecoder.com

# Expected: HTTP/2 200
# Server: Traefik
```

### 4. Subdomain Routing Test
```bash
# Test company subdomain
curl -I https://testco.youarecoder.com

# Test workspace subdomain (after workspace creation)
curl -I https://dev-testco.youarecoder.com
```

---

## 🔧 Troubleshooting

### Issue: DNS not propagating

**Solution 1: Check DNS servers**
```bash
# Check if DNS is set correctly
nslookup youarecoder.com 8.8.8.8
nslookup testco.youarecoder.com 8.8.8.8
```

**Solution 2: Flush local DNS cache**
```bash
# Linux
sudo systemd-resolve --flush-caches

# macOS
sudo dscacheutil -flushcache

# Windows
ipconfig /flushdns
```

**Solution 3: Wait longer**
DNS propagation can take up to 24-48 hours globally. Use https://dnschecker.org to monitor.

### Issue: SSL certificate not generating

**Check 1: Verify DNS is propagated**
```bash
dig youarecoder.com +short
# Must return: 46.62.150.235
```

**Check 2: Verify HTTP is accessible**
```bash
curl -I http://youarecoder.com
# Should work and redirect to HTTPS
```

**Check 3: Check Traefik logs**
```bash
sudo journalctl -u traefik -n 50 -f
# Look for ACME/Let's Encrypt errors
```

**Check 4: Verify ports 80 and 443 are open**
```bash
sudo ufw status
# Both 80/tcp and 443/tcp should be ALLOW
```

### Issue: Wildcard subdomain not working

**Check wildcard DNS:**
```bash
# Should return 46.62.150.235 for ANY subdomain
dig random-subdomain.youarecoder.com +short
dig another-test.youarecoder.com +short
```

**Check Traefik routing:**
```bash
# View Traefik dashboard (if enabled)
curl http://localhost:8080/api/http/routers
```

---

## 📅 Migration Plan (Production)

### Phase 1: DNS Setup (Day 0)
- ✅ Add DNS records (A + wildcard)
- ✅ Verify propagation (1-2 hours)
- ✅ Document current status

### Phase 2: SSL Certificate (Day 0)
- ⏳ Start Traefik service
- ⏳ Automatic certificate generation
- ⏳ Verify HTTPS access

### Phase 3: Application Deployment (Day 1)
- ⏳ Deploy Flask application
- ⏳ Configure database
- ⏳ Test company registration
- ⏳ Test workspace creation

### Phase 4: Production Switch (Day 2)
- ⏳ Update DNS to production server (37.27.21.167)
- ⏳ Wait for propagation (1-2 hours)
- ⏳ Verify all services
- ⏳ Go live

---

## 🚨 Important Notes

### Security Considerations

1. **Firewall Rules:**
   ```bash
   sudo ufw allow 80/tcp   # HTTP
   sudo ufw allow 443/tcp  # HTTPS
   sudo ufw allow 22/tcp   # SSH (be careful!)
   ```

2. **Let's Encrypt Rate Limits:**
   - 50 certificates per domain per week
   - 5 failed validations per hour
   - Use staging environment for testing

3. **DNS TTL:**
   - Use low TTL (300s) during setup
   - Increase to 3600s after stable

### Backup DNS Configuration

**Export current DNS settings:**
```bash
# Save current DNS records
dig youarecoder.com ANY > dns-backup-$(date +%Y%m%d).txt
```

**Document in secure location:**
- Domain registrar credentials
- DNS record screenshots
- SSL certificate backup

---

## 📞 Support Resources

### DNS Propagation Checkers
- https://dnschecker.org
- https://www.whatsmydns.net
- https://mxtoolbox.com

### SSL Certificate Validators
- https://www.ssllabs.com/ssltest/
- https://letsencrypt.org/docs/

### Traefik Documentation
- https://doc.traefik.io/traefik/

---

## ✅ Checklist

### Pre-Deployment
- [ ] Domain purchased and accessible
- [ ] Server IP confirmed (46.62.150.235)
- [ ] Traefik installed and configured
- [ ] Firewall ports opened (80, 443)

### DNS Setup
- [ ] A record added for root domain
- [ ] Wildcard A record added
- [ ] DNS propagation verified (dnschecker.org)
- [ ] Local DNS cache flushed

### SSL Certificate
- [ ] Traefik service running
- [ ] HTTP accessible (curl test)
- [ ] HTTPS certificate generated
- [ ] Certificate valid and trusted

### Application Testing
- [ ] Landing page accessible (https://youarecoder.com)
- [ ] Company registration works
- [ ] Company subdomain accessible (https://{company}.youarecoder.com)
- [ ] Workspace creation tested
- [ ] Workspace subdomain accessible (https://{workspace}-{company}.youarecoder.com)

### Production Ready
- [ ] All tests passing
- [ ] Documentation complete
- [ ] Monitoring configured
- [ ] Backup strategy in place

---

**Last Updated:** 2025-10-27
**Status:** Ready for DNS setup
**Next Step:** Add DNS records at domain registrar

