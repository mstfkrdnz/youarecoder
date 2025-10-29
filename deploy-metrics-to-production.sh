#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

APP_DIR="/root/youarecoder"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}YouAreCoder Metrics Collection Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Step 1: Pull latest code
echo -e "${YELLOW}[1/8] Pulling latest code from GitHub...${NC}"
cd $APP_DIR
git pull origin main
echo -e "${GREEN}✓ Code updated${NC}"
echo ""

# Step 2: Apply database migration
echo -e "${YELLOW}[2/8] Applying database migration...${NC}"
source venv/bin/activate
python run_migrations.py
echo -e "${GREEN}✓ Migration applied${NC}"
echo ""

# Step 3: Verify Flask CLI commands
echo -e "${YELLOW}[3/8] Verifying Flask CLI commands...${NC}"
flask --help | grep -q "collect-metrics" && echo "  ✓ collect-metrics command registered" || echo "  ✗ collect-metrics command NOT found"
flask --help | grep -q "cleanup-metrics" && echo "  ✓ cleanup-metrics command registered" || echo "  ✗ cleanup-metrics command NOT found"
echo ""

# Step 4: Install systemd service files
echo -e "${YELLOW}[4/8] Installing systemd service files...${NC}"
cp systemd/youarecoder-metrics-collector.service /etc/systemd/system/
cp systemd/youarecoder-metrics-collector.timer /etc/systemd/system/
systemctl daemon-reload
echo -e "${GREEN}✓ Systemd files installed${NC}"
echo ""

# Step 5: Enable and start timer
echo -e "${YELLOW}[5/8] Enabling and starting metrics collector timer...${NC}"
systemctl enable youarecoder-metrics-collector.timer
systemctl start youarecoder-metrics-collector.timer
echo -e "${GREEN}✓ Timer enabled and started${NC}"
echo ""

# Step 6: Verify timer is running
echo -e "${YELLOW}[6/8] Verifying timer status...${NC}"
systemctl status youarecoder-metrics-collector.timer --no-pager | head -10
echo ""

# Step 7: Restart Flask application
echo -e "${YELLOW}[7/8] Restarting Flask application...${NC}"
systemctl restart youarecoder
sleep 3
systemctl status youarecoder --no-pager | head -10
echo -e "${GREEN}✓ Flask application restarted${NC}"
echo ""

# Step 8: Test metrics collection manually
echo -e "${YELLOW}[8/8] Testing metrics collection...${NC}"
flask collect-metrics
echo -e "${GREEN}✓ Manual metrics collection test complete${NC}"
echo ""

# Display timer schedule
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Summary${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Metrics Collector Timer Schedule:"
systemctl list-timers --no-pager | grep youarecoder-metrics
echo ""
echo -e "${GREEN}✓ Deployment complete!${NC}"
echo ""
echo "Metrics collection will run every 10 minutes."
echo ""
echo "Monitor logs with:"
echo "  journalctl -u youarecoder-metrics-collector.service -f"
echo ""
echo "API endpoints:"
echo "  GET /api/metrics/workspaces/{id}"
echo "  GET /api/metrics/workspaces/{id}/current"
echo "  GET /api/metrics/workspaces/{id}/summary"
echo "  GET /api/metrics/overview (admin only)"
