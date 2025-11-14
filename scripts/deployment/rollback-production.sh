#!/bin/bash

# YouAreCoder Production Rollback Script
# Rollback to previous commit on production server

set -e

PRODUCTION_SERVER="root@37.27.21.167"
PRODUCTION_PATH="/root/youarecoder"
SERVICE_NAME="youarecoder"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_step() {
    echo -e "${BLUE}➜${NC} $1"
}

print_success() {
    echo -e "${GREEN}✅${NC} $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC}  $1"
}

echo ""
print_warning "PRODUCTION ROLLBACK"
echo ""
print_step "This will rollback production to the previous commit"
echo ""

read -p "Continue with rollback? (yes/no) " -r
echo
if [[ ! $REPLY == "yes" ]]; then
    print_warning "Rollback cancelled"
    exit 0
fi

# Create rollback script
ROLLBACK_SCRIPT=$(cat <<'REMOTESCRIPT'
#!/bin/bash
set -e

PROD_PATH="/root/youarecoder"
SERVICE_NAME="youarecoder"

echo "🔵 Entering production directory..."
cd $PROD_PATH

echo "🔵 Getting previous commit..."
if [[ ! -f /tmp/youarecoder_previous_commit.txt ]]; then
    echo "❌ No previous commit found in /tmp/youarecoder_previous_commit.txt"
    echo "Cannot perform automatic rollback"
    exit 1
fi

PREVIOUS_COMMIT=$(cat /tmp/youarecoder_previous_commit.txt)
CURRENT_COMMIT=$(git rev-parse --short HEAD)

echo "  Current commit: $CURRENT_COMMIT"
echo "  Rolling back to: $PREVIOUS_COMMIT"

echo "🔵 Resetting to previous commit..."
git reset --hard $PREVIOUS_COMMIT

echo "🔵 Activating virtual environment..."
source venv/bin/activate

echo "🔵 Reinstalling dependencies (in case they changed)..."
pip install -q -r requirements.txt

# Note: Migrations are handled separately if needed
# Production database is managed through direct SQL or manual migration scripts

echo "🔵 Restarting service..."
sudo systemctl restart $SERVICE_NAME

echo "🔵 Checking service status..."
sleep 2
if sudo systemctl is-active --quiet $SERVICE_NAME; then
    echo "✅ Service is running"
    echo "✅ Rollback successful!"
    echo "   Rolled back from: $CURRENT_COMMIT"
    echo "   Current commit: $(git rev-parse --short HEAD)"
else
    echo "❌ Service failed to start after rollback!"
    sudo systemctl status $SERVICE_NAME
    exit 1
fi
REMOTESCRIPT
)

print_step "Connecting to production server..."
ssh $PRODUCTION_SERVER "bash -s" <<< "$ROLLBACK_SCRIPT"

if [[ $? -eq 0 ]]; then
    echo ""
    print_success "🔄 Production rollback complete!"
    print_success "Visit: https://youarecoder.com"
    echo ""
else
    echo ""
    print_error "Rollback failed - check logs above"
    exit 1
fi
