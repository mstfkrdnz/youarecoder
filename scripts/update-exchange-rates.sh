#!/bin/bash
# Update exchange rates from TCMB (Turkish Central Bank)
# This script should be run daily via cron at 16:00, 17:00, 18:00

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="/var/log/youarecoder/exchange-rates.log"

# Create log directory if it doesn't exist
sudo mkdir -p /var/log/youarecoder
sudo chown mustafa:mustafa /var/log/youarecoder 2>/dev/null || true

# Change to project directory
cd "$PROJECT_DIR"

# Log start
echo "================================================================" >> "$LOG_FILE"
echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting exchange rate update" >> "$LOG_FILE"

# Activate virtual environment
source venv/bin/activate

# Run Flask CLI command
FLASK_APP=app flask update-exchange-rates >> "$LOG_FILE" 2>&1

# Check exit code
if [ $? -eq 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - ✅ Exchange rates updated successfully" >> "$LOG_FILE"
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') - ❌ Exchange rate update failed" >> "$LOG_FILE"
fi

echo "" >> "$LOG_FILE"
