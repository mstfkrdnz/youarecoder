#!/bin/bash

# YouAreCoder Health Check Script
# Monitors system health and sends alerts when issues detected

set -e

# Load environment variables
if [ -f /root/youarecoder/.env ]; then
    set -a
    source /root/youarecoder/.env
    set +a
fi

# Configuration
LOG_FILE="/var/log/youarecoder/health-check.log"
ALERT_EMAIL=""  # Set email for alerts
MIN_DISK_SPACE=20  # Percentage
MAX_CPU_LOAD=80    # Percentage
MAX_MEMORY_USAGE=90  # Percentage

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Initialize
mkdir -p "$(dirname "$LOG_FILE")"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
ISSUES=()

# Log function
log() {
    echo "[$TIMESTAMP] $1" | tee -a "$LOG_FILE"
}

# Check function
check() {
    local status=$1
    local name=$2
    local message=$3

    if [ "$status" = "OK" ]; then
        echo -e "${GREEN}✅ $name: $message${NC}"
        log "✅ $name: $message"
    elif [ "$status" = "WARNING" ]; then
        echo -e "${YELLOW}⚠️  $name: $message${NC}"
        log "⚠️  $name: $message"
        ISSUES+=("WARNING: $name - $message")
    else
        echo -e "${RED}❌ $name: $message${NC}"
        log "❌ $name: $message"
        ISSUES+=("CRITICAL: $name - $message")
    fi
}

echo "================================================"
echo "YouAreCoder Health Check - $TIMESTAMP"
echo "================================================"
echo ""

# 1. Check Systemd Services
echo "🔍 Checking Services..."
if systemctl is-active --quiet youarecoder.service; then
    check "OK" "Flask Service" "Running"
else
    check "CRITICAL" "Flask Service" "Not running!"
fi

if systemctl is-active --quiet traefik.service; then
    check "OK" "Traefik Service" "Running"
else
    check "CRITICAL" "Traefik Service" "Not running!"
fi

if systemctl is-active --quiet postgresql.service; then
    check "OK" "PostgreSQL" "Running"
else
    check "CRITICAL" "PostgreSQL" "Not running!"
fi

echo ""

# 2. Check HTTP Endpoints
echo "🌐 Checking HTTP Endpoints..."
if curl -s -o /dev/null -w "%{http_code}" -L --max-time 10 https://youarecoder.com | grep -q "200\|302"; then
    check "OK" "Main Site" "Accessible (HTTP 200/302)"
else
    check "CRITICAL" "Main Site" "Not accessible!"
fi

echo ""

# 3. Check Disk Space
echo "💾 Checking Disk Space..."
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
    check "CRITICAL" "Root Disk" "${DISK_USAGE}% used (critical)!"
elif [ "$DISK_USAGE" -gt 70 ]; then
    check "WARNING" "Root Disk" "${DISK_USAGE}% used"
else
    check "OK" "Root Disk" "${DISK_USAGE}% used"
fi

BACKUP_DISK_USAGE=$(df -h /var/backups 2>/dev/null | awk 'NR==2 {print $5}' | sed 's/%//' || echo "0")
if [ "$BACKUP_DISK_USAGE" -gt 80 ]; then
    check "WARNING" "Backup Disk" "${BACKUP_DISK_USAGE}% used"
else
    check "OK" "Backup Disk" "${BACKUP_DISK_USAGE}% used"
fi

echo ""

# 4. Check Memory Usage
echo "🧠 Checking Memory..."
MEMORY_USAGE=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
if [ "$MEMORY_USAGE" -gt "$MAX_MEMORY_USAGE" ]; then
    check "CRITICAL" "Memory" "${MEMORY_USAGE}% used!"
elif [ "$MEMORY_USAGE" -gt 75 ]; then
    check "WARNING" "Memory" "${MEMORY_USAGE}% used"
else
    check "OK" "Memory" "${MEMORY_USAGE}% used"
fi

echo ""

# 5. Check CPU Load
echo "⚡ Checking CPU..."
CPU_LOAD=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}' | cut -d'.' -f1)
if [ "$CPU_LOAD" -gt "$MAX_CPU_LOAD" ]; then
    check "WARNING" "CPU Load" "${CPU_LOAD}% used"
else
    check "OK" "CPU Load" "${CPU_LOAD}% used"
fi

echo ""

# 6. Check Database
echo "🗄️  Checking Database..."
DB_USER="${DB_USER:-youarecoder_user}"
DB_NAME="${DB_NAME:-youarecoder}"
DB_HOST="${DB_HOST:-localhost}"
if PGPASSWORD="${DB_PASS}" psql -h "${DB_HOST}" -U "${DB_USER}" -d "${DB_NAME}" -c "SELECT 1" > /dev/null 2>&1; then
    check "OK" "Database" "Accessible"
else
    check "CRITICAL" "Database" "Connection failed!"
fi

echo ""

# 7. Check SSL Certificate
echo "🔐 Checking SSL Certificate..."
CERT_EXPIRY=$(echo | openssl s_client -servername youarecoder.com -connect youarecoder.com:443 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
if [ -n "$CERT_EXPIRY" ]; then
    DAYS_LEFT=$(( ( $(date -d "$CERT_EXPIRY" +%s) - $(date +%s) ) / 86400 ))
    if [ "$DAYS_LEFT" -lt 7 ]; then
        check "CRITICAL" "SSL Certificate" "Expires in ${DAYS_LEFT} days!"
    elif [ "$DAYS_LEFT" -lt 30 ]; then
        check "WARNING" "SSL Certificate" "Expires in ${DAYS_LEFT} days"
    else
        check "OK" "SSL Certificate" "Valid for ${DAYS_LEFT} days"
    fi
else
    check "WARNING" "SSL Certificate" "Could not verify"
fi

echo ""

# 8. Check Backups
echo "💾 Checking Backups..."
LATEST_BACKUP=$(find /var/backups/youarecoder/database -name "youarecoder_*.sql.gz" -type f -mtime -2 | head -1)
if [ -n "$LATEST_BACKUP" ]; then
    BACKUP_AGE=$(find /var/backups/youarecoder/database -name "youarecoder_*.sql.gz" -type f -mtime -2 | wc -l)
    check "OK" "Recent Backup" "Found (< 48 hours old)"
else
    check "WARNING" "Recent Backup" "No recent backup found!"
fi

echo ""
echo "================================================"

# Summary
if [ ${#ISSUES[@]} -eq 0 ]; then
    echo -e "${GREEN}✅ ALL CHECKS PASSED${NC}"
    log "✅ All health checks passed"
    exit 0
else
    echo -e "${RED}⚠️  ${#ISSUES[@]} ISSUE(S) DETECTED${NC}"
    echo ""
    for issue in "${ISSUES[@]}"; do
        echo -e "${YELLOW}  - $issue${NC}"
    done
    log "⚠️  ${#ISSUES[@]} issues detected"

    # Send alert if email configured
    if [ -n "$ALERT_EMAIL" ]; then
        {
            echo "Subject: YouAreCoder Health Alert"
            echo ""
            echo "Issues detected on $(hostname):"
            echo ""
            for issue in "${ISSUES[@]}"; do
                echo "  - $issue"
            done
        } | sendmail "$ALERT_EMAIL" 2>/dev/null || true
    fi

    exit 1
fi
