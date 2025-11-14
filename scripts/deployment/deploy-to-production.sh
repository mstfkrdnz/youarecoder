#!/bin/bash

# YouAreCoder Production Deployment Script
# Deploy from GitHub to production server safely

set -e  # Exit on any error

# Configuration
PRODUCTION_SERVER="root@37.27.21.167"
PRODUCTION_PATH="/var/www/youarecoder"
SERVICE_NAME="youarecoder"
BRANCH="main"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Dry run mode
DRY_RUN=false
if [[ "$1" == "--dry-run" ]] || [[ "$1" == "-d" ]]; then
    DRY_RUN=true
    echo -e "${YELLOW}🧪 DRY RUN MODE - No changes will be made${NC}"
    echo ""
fi

# Helper function to print colored messages
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

# Validate we're in the correct directory
if [[ ! -f "run.py" ]] || [[ ! -d "app" ]]; then
    print_error "Must run from youarecoder project root"
    exit 1
fi

# Check if we're on the correct branch
print_step "Checking current branch..."
CURRENT_BRANCH=$(git branch --show-current)
if [[ "$CURRENT_BRANCH" != "$BRANCH" ]]; then
    print_error "Currently on branch '$CURRENT_BRANCH', must be on '$BRANCH'"
    exit 1
fi
print_success "On correct branch: $BRANCH"

# Check for uncommitted changes
print_step "Checking for uncommitted changes..."
if [[ -n $(git status --porcelain) ]]; then
    print_error "You have uncommitted changes. Commit and push before deploying."
    git status --short
    exit 1
fi
print_success "No uncommitted changes"

# Check if local is behind remote
print_step "Checking if local is up to date with remote..."
git fetch origin $BRANCH
LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse @{u})

if [[ $LOCAL != $REMOTE ]]; then
    print_error "Local branch is not in sync with remote"
    echo "Run: git pull origin $BRANCH"
    exit 1
fi
print_success "Local is up to date with remote"

# Get current commit info
COMMIT_HASH=$(git rev-parse --short HEAD)
COMMIT_MSG=$(git log -1 --pretty=%B)
print_step "Current commit: $COMMIT_HASH"
echo "  Message: $COMMIT_MSG"

# Confirm deployment
echo ""
print_warning "Ready to deploy to PRODUCTION"
echo "  Server: $PRODUCTION_SERVER"
echo "  Path: $PRODUCTION_PATH"
echo "  Commit: $COMMIT_HASH"
echo ""

if [[ "$DRY_RUN" == "false" ]]; then
    read -p "Continue with deployment? (yes/no) " -r
    echo
    if [[ ! $REPLY == "yes" ]]; then
        print_warning "Deployment cancelled"
        exit 0
    fi
fi

# Create deployment script to run on production
DEPLOY_SCRIPT=$(cat <<'REMOTESCRIPT'
#!/bin/bash
set -e

PROD_PATH="/var/www/youarecoder"
SERVICE_NAME="youarecoder"

echo "🔵 Entering production directory..."
cd $PROD_PATH

echo "🔵 Saving current commit (for rollback)..."
PREVIOUS_COMMIT=$(git rev-parse --short HEAD)
echo $PREVIOUS_COMMIT > /tmp/youarecoder_previous_commit.txt

echo "🔵 Pulling latest changes from GitHub..."
git fetch origin main
git reset --hard origin/main

echo "🔵 Activating virtual environment..."
source venv/bin/activate

echo "🔵 Installing/updating dependencies..."
pip install -q -r requirements.txt

echo "🔵 Running database migrations..."
export FLASK_APP=app
flask db upgrade

echo "🔵 Restarting application service..."
sudo systemctl restart $SERVICE_NAME

echo "🔵 Checking service status..."
sleep 2
if sudo systemctl is-active --quiet $SERVICE_NAME; then
    echo "✅ Service is running"
    echo "✅ Deployment successful!"
    echo "   Previous commit: $PREVIOUS_COMMIT"
    echo "   Current commit: $(git rev-parse --short HEAD)"
else
    echo "❌ Service failed to start!"
    echo "🔄 Rolling back to previous commit..."
    git reset --hard $PREVIOUS_COMMIT
    sudo systemctl restart $SERVICE_NAME
    exit 1
fi
REMOTESCRIPT
)

# Execute deployment
print_step "Connecting to production server..."

if [[ "$DRY_RUN" == "true" ]]; then
    print_success "DRY RUN: Would execute deployment script on $PRODUCTION_SERVER"
    echo ""
    echo "Deployment script that would be executed:"
    echo "----------------------------------------"
    echo "$DEPLOY_SCRIPT"
    echo "----------------------------------------"
    print_success "DRY RUN complete - no changes made"
else
    ssh $PRODUCTION_SERVER "bash -s" <<< "$DEPLOY_SCRIPT"

    if [[ $? -eq 0 ]]; then
        echo ""
        print_success "🚀 Production deployment complete!"
        print_success "Visit: https://youarecoder.com"
        echo ""
        print_step "Deployment log saved"
        echo "  Commit: $COMMIT_HASH"
        echo "  Time: $(date)"
    else
        echo ""
        print_error "Deployment failed - check logs above"
        exit 1
    fi
fi
