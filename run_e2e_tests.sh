#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}YouAreCoder E2E Test Suite${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Configuration
TEST_FILE="tests/test_e2e_comprehensive_features.py"
COVERAGE_DIR="htmlcov"

# Use system Python
echo -e "${YELLOW}[1/5] Checking Python environment...${NC}"
python3 --version
echo -e "${GREEN}✓ Python environment ready${NC}"
echo ""

# Install test dependencies
echo -e "${YELLOW}[2/5] Installing test dependencies...${NC}"
pip install -q pytest pytest-playwright pytest-cov pytest-html playwright 2>&1 | grep -v "already satisfied" || true
python -m playwright install chromium 2>&1 | tail -5
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Run E2E tests with coverage
echo -e "${YELLOW}[3/5] Running E2E test suite...${NC}"
echo ""
echo -e "${BLUE}Test Features Covered:${NC}"
echo "  • Owner Team Management (add/remove/role change)"
echo "  • Developer Workspace Quota Enforcement (plan limits)"
echo "  • Template Provisioning (Python, React templates)"
echo "  • Workspace Lifecycle (start/stop/restart)"
echo "  • PayTR Checkout (billing and subscription)"
echo ""

pytest $TEST_FILE \
    -v \
    --tb=short \
    --maxfail=5 \
    --color=yes \
    -m e2e \
    --cov=app \
    --cov-report=html \
    --cov-report=term-missing \
    --html=test-report.html \
    --self-contained-html 2>&1 | tee test-output.log

TEST_EXIT_CODE=$?

echo ""
echo -e "${YELLOW}[4/5] Generating coverage report...${NC}"

if [ -d "$COVERAGE_DIR" ]; then
    echo -e "${GREEN}✓ Coverage HTML report: ${COVERAGE_DIR}/index.html${NC}"
else
    echo -e "${YELLOW}⚠ Coverage report directory not found${NC}"
fi

echo ""
echo -e "${YELLOW}[5/5] Test Execution Summary${NC}"
echo -e "${BLUE}========================================${NC}"

# Parse test results
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ All tests PASSED${NC}"
else
    echo -e "${RED}✗ Some tests FAILED (exit code: $TEST_EXIT_CODE)${NC}"
fi

# Count test results from log
PASSED=$(grep -oP '\d+(?= passed)' test-output.log | head -1 || echo "0")
FAILED=$(grep -oP '\d+(?= failed)' test-output.log | head -1 || echo "0")
SKIPPED=$(grep -oP '\d+(?= skipped)' test-output.log | head -1 || echo "0")

echo ""
echo -e "${BLUE}Test Results:${NC}"
echo -e "  Passed:  ${GREEN}$PASSED${NC}"
echo -e "  Failed:  ${RED}$FAILED${NC}"
echo -e "  Skipped: ${YELLOW}$SKIPPED${NC}"

# Show coverage summary
echo ""
echo -e "${BLUE}Coverage Summary:${NC}"
grep -A 5 "^TOTAL" test-output.log || echo "Coverage data not available"

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Artifacts Generated:${NC}"
echo -e "  • Test Log: test-output.log"
echo -e "  • HTML Report: test-report.html"
echo -e "  • Coverage: ${COVERAGE_DIR}/index.html"
echo -e "  • Screenshots: /tmp/youarecoder_e2e/*.png"
echo ""

# Cleanup on success
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ E2E Test Suite Completed Successfully${NC}"
else
    echo -e "${RED}✗ E2E Test Suite Completed with Failures${NC}"
    echo ""
    echo -e "${YELLOW}To debug:${NC}"
    echo "  1. Review test-output.log for detailed errors"
    echo "  2. Check screenshots in /tmp/youarecoder_e2e/"
    echo "  3. Open test-report.html in browser for HTML report"
fi

echo ""

exit $TEST_EXIT_CODE
