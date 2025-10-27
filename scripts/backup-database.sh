#!/bin/bash

# PostgreSQL Database Backup Script for YouAreCoder
# Automated daily backups with retention policy

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
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/youarecoder_${TIMESTAMP}.sql.gz"
LOG_FILE="/var/log/youarecoder/backup.log"

# Ensure backup directory exists
mkdir -p "${BACKUP_DIR}"
mkdir -p "$(dirname "${LOG_FILE}")"

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

log "Starting database backup..."

# Create backup
export PGPASSWORD="${DB_PASS}"
if pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" | gzip > "${BACKUP_FILE}"; then
    BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
    log "✅ Backup successful: ${BACKUP_FILE} (${BACKUP_SIZE})"
else
    log "❌ Backup failed!"
    exit 1
fi

# Verify backup integrity
if gunzip -t "${BACKUP_FILE}" 2>/dev/null; then
    log "✅ Backup integrity verified"
else
    log "❌ Backup integrity check failed!"
    exit 1
fi

# Remove old backups (older than RETENTION_DAYS)
log "Removing backups older than ${RETENTION_DAYS} days..."
DELETED_COUNT=$(find "${BACKUP_DIR}" -name "youarecoder_*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete -print | wc -l)
log "Removed ${DELETED_COUNT} old backup(s)"

# List current backups
BACKUP_COUNT=$(find "${BACKUP_DIR}" -name "youarecoder_*.sql.gz" -type f | wc -l)
TOTAL_SIZE=$(du -sh "${BACKUP_DIR}" | cut -f1)
log "Current backups: ${BACKUP_COUNT} files, Total size: ${TOTAL_SIZE}"

log "Backup completed successfully"
