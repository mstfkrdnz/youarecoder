#!/bin/bash

# PostgreSQL Database Restore Script for YouAreCoder
# Restore from backup with safety checks

set -e

# Load environment variables
if [ -f /root/youarecoder/.env ]; then
    set -a
    source /root/youarecoder/.env
    set +a
fi

# Configuration
DB_NAME="${DB_NAME:-youarecoder}"
DB_USER="${DB_USER:-youarecoder_user}"
DB_PASS="${DB_PASS:-}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
BACKUP_DIR="/var/backups/youarecoder/database"
LOG_FILE="/var/log/youarecoder/restore.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

# Usage function
usage() {
    echo "Usage: $0 <backup_file>"
    echo ""
    echo "Available backups:"
    ls -lh "${BACKUP_DIR}"/youarecoder_*.sql.gz 2>/dev/null | tail -10 || echo "No backups found"
    exit 1
}

# Check if backup file provided
if [ $# -eq 0 ]; then
    usage
fi

BACKUP_FILE="$1"

# Check if backup file exists
if [ ! -f "${BACKUP_FILE}" ]; then
    echo -e "${RED}❌ Backup file not found: ${BACKUP_FILE}${NC}"
    usage
fi

# Verify backup integrity
echo -e "${YELLOW}⏳ Verifying backup integrity...${NC}"
if ! gunzip -t "${BACKUP_FILE}" 2>/dev/null; then
    echo -e "${RED}❌ Backup file is corrupted!${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Backup integrity verified${NC}"

# Safety confirmation
echo -e "${RED}⚠️  WARNING: This will OVERWRITE the current database!${NC}"
echo -e "${YELLOW}Database: ${DB_NAME}${NC}"
echo -e "${YELLOW}Backup: ${BACKUP_FILE}${NC}"
echo ""
read -p "Are you sure you want to continue? (yes/no): " -r
if [[ ! $REPLY =~ ^yes$ ]]; then
    echo "Restore cancelled"
    exit 0
fi

log "Starting database restore from ${BACKUP_FILE}..."

# Set PostgreSQL password
export PGPASSWORD="${DB_PASS}"

# Create a safety backup before restore
SAFETY_BACKUP="/tmp/youarecoder_pre_restore_$(date +%Y%m%d_%H%M%S).sql.gz"
echo -e "${YELLOW}⏳ Creating safety backup...${NC}"
if pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" | gzip > "${SAFETY_BACKUP}"; then
    echo -e "${GREEN}✅ Safety backup created: ${SAFETY_BACKUP}${NC}"
    log "Safety backup created: ${SAFETY_BACKUP}"
else
    echo -e "${RED}❌ Safety backup failed! Aborting restore.${NC}"
    exit 1
fi

# Stop application during restore
echo -e "${YELLOW}⏳ Stopping application...${NC}"
systemctl stop youarecoder.service

# Perform restore
echo -e "${YELLOW}⏳ Restoring database...${NC}"
if gunzip -c "${BACKUP_FILE}" | psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}"; then
    echo -e "${GREEN}✅ Database restored successfully${NC}"
    log "✅ Restore successful from ${BACKUP_FILE}"
else
    echo -e "${RED}❌ Restore failed!${NC}"
    log "❌ Restore failed from ${BACKUP_FILE}"

    # Attempt to restore safety backup
    echo -e "${YELLOW}⏳ Attempting to restore safety backup...${NC}"
    if gunzip -c "${SAFETY_BACKUP}" | psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}"; then
        echo -e "${GREEN}✅ Safety backup restored${NC}"
        log "✅ Rolled back to safety backup"
    else
        echo -e "${RED}❌ Safety backup restore failed! DATABASE MAY BE IN INCONSISTENT STATE!${NC}"
        log "❌ CRITICAL: Safety backup restore failed"
    fi

    exit 1
fi

# Start application
echo -e "${YELLOW}⏳ Starting application...${NC}"
systemctl start youarecoder.service

# Wait for service to be ready
sleep 5

# Check service status
if systemctl is-active --quiet youarecoder.service; then
    echo -e "${GREEN}✅ Application started successfully${NC}"
    log "Application restarted after restore"
else
    echo -e "${RED}❌ Application failed to start!${NC}"
    log "❌ Application failed to start after restore"
    exit 1
fi

echo -e "${GREEN}✅ Restore completed successfully${NC}"
echo -e "${YELLOW}Safety backup: ${SAFETY_BACKUP}${NC}"
log "Restore completed successfully"
