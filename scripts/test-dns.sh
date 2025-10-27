#!/bin/bash
# DNS Test Script for YouAreCoder.com
# Tests DNS configuration and subdomain routing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Expected IP address
EXPECTED_IP_PROD="37.27.21.167"
EXPECTED_IP_DEV="46.62.150.235"

echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}  YouAreCoder DNS Test Suite${NC}"
echo -e "${BLUE}=====================================${NC}"
echo ""

# Test counter
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Test function
test_dns() {
    local domain=$1
    local description=$2
    local expected_ip=$3

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    echo -e "${YELLOW}Testing:${NC} $domain ($description)"

    # Perform DNS lookup
    result=$(dig $domain +short 2>/dev/null | head -n1)

    if [ -z "$result" ]; then
        echo -e "${RED}  ✗ FAILED:${NC} No DNS record found"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi

    if [ "$result" == "$expected_ip" ]; then
        echo -e "${GREEN}  ✓ PASSED:${NC} $result (expected: $expected_ip)"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}  ✗ FAILED:${NC} $result (expected: $expected_ip)"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# Determine which server to test
echo -e "${YELLOW}Which server to test?${NC}"
echo "1) Production (37.27.21.167)"
echo "2) Development (46.62.150.235)"
echo "3) Both"
read -p "Choice [1-3]: " server_choice

case $server_choice in
    1)
        EXPECTED_IP=$EXPECTED_IP_PROD
        echo -e "${BLUE}Testing Production Server: $EXPECTED_IP${NC}"
        echo ""
        ;;
    2)
        EXPECTED_IP=$EXPECTED_IP_DEV
        echo -e "${BLUE}Testing Development Server: $EXPECTED_IP${NC}"
        echo ""
        ;;
    3)
        echo -e "${BLUE}Testing Both Servers${NC}"
        echo ""
        # Run tests for prod
        echo -e "${YELLOW}=== Production Server Tests ===${NC}"
        EXPECTED_IP=$EXPECTED_IP_PROD
        test_dns "youarecoder.com" "Root domain" "$EXPECTED_IP"
        test_dns "www.youarecoder.com" "WWW subdomain" "$EXPECTED_IP"
        test_dns "testco.youarecoder.com" "Company subdomain" "$EXPECTED_IP"
        test_dns "dev-testco.youarecoder.com" "Workspace subdomain" "$EXPECTED_IP"

        echo ""
        echo -e "${YELLOW}=== Development Server Tests ===${NC}"
        EXPECTED_IP=$EXPECTED_IP_DEV
        test_dns "youarecoder.com" "Root domain" "$EXPECTED_IP"
        test_dns "www.youarecoder.com" "WWW subdomain" "$EXPECTED_IP"
        test_dns "testco.youarecoder.com" "Company subdomain" "$EXPECTED_IP"
        test_dns "dev-testco.youarecoder.com" "Workspace subdomain" "$EXPECTED_IP"

        # Summary and exit
        echo ""
        echo -e "${BLUE}=====================================${NC}"
        echo -e "${BLUE}  Test Summary${NC}"
        echo -e "${BLUE}=====================================${NC}"
        echo -e "Total Tests:  $TOTAL_TESTS"
        echo -e "${GREEN}Passed:       $PASSED_TESTS${NC}"
        echo -e "${RED}Failed:       $FAILED_TESTS${NC}"

        if [ $FAILED_TESTS -eq 0 ]; then
            echo ""
            echo -e "${GREEN}✓ All DNS tests passed!${NC}"
            exit 0
        else
            echo ""
            echo -e "${RED}✗ Some DNS tests failed${NC}"
            exit 1
        fi
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

# Run standard test suite
echo -e "${YELLOW}=== Core DNS Tests ===${NC}"
test_dns "youarecoder.com" "Root domain" "$EXPECTED_IP"
test_dns "www.youarecoder.com" "WWW subdomain" "$EXPECTED_IP"

echo ""
echo -e "${YELLOW}=== Wildcard DNS Tests ===${NC}"
test_dns "testco.youarecoder.com" "Company subdomain (testco)" "$EXPECTED_IP"
test_dns "acmecorp.youarecoder.com" "Company subdomain (acmecorp)" "$EXPECTED_IP"
test_dns "startup123.youarecoder.com" "Company subdomain (startup123)" "$EXPECTED_IP"

echo ""
echo -e "${YELLOW}=== Workspace DNS Tests ===${NC}"
test_dns "dev-testco.youarecoder.com" "Workspace subdomain (dev-testco)" "$EXPECTED_IP"
test_dns "john-acmecorp.youarecoder.com" "Workspace subdomain (john-acmecorp)" "$EXPECTED_IP"
test_dns "staging-startup123.youarecoder.com" "Workspace subdomain (staging-startup123)" "$EXPECTED_IP"

echo ""
echo -e "${YELLOW}=== Random Subdomain Tests (Wildcard Verification) ===${NC}"
test_dns "random123.youarecoder.com" "Random subdomain test 1" "$EXPECTED_IP"
test_dns "test-xyz.youarecoder.com" "Random subdomain test 2" "$EXPECTED_IP"
test_dns "anything-works.youarecoder.com" "Random subdomain test 3" "$EXPECTED_IP"

# DNS Propagation Check
echo ""
echo -e "${YELLOW}=== DNS Propagation Check ===${NC}"
echo "Checking DNS from multiple servers..."

for dns_server in "8.8.8.8" "1.1.1.1" "208.67.222.222"; do
    echo -e "${YELLOW}Checking via $dns_server:${NC}"
    result=$(dig @$dns_server youarecoder.com +short 2>/dev/null | head -n1)
    if [ "$result" == "$EXPECTED_IP" ]; then
        echo -e "${GREEN}  ✓ $result${NC}"
    else
        echo -e "${RED}  ✗ $result (expected: $EXPECTED_IP)${NC}"
        echo -e "${YELLOW}    Note: DNS may still be propagating${NC}"
    fi
done

# Summary
echo ""
echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}  Test Summary${NC}"
echo -e "${BLUE}=====================================${NC}"
echo -e "Total Tests:  $TOTAL_TESTS"
echo -e "${GREEN}Passed:       $PASSED_TESTS${NC}"
echo -e "${RED}Failed:       $FAILED_TESTS${NC}"

if [ $FAILED_TESTS -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ All DNS tests passed!${NC}"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "1. Start Traefik service"
    echo "2. Start Flask application"
    echo "3. Test HTTPS access"
    echo "4. Generate SSL certificates"
    exit 0
else
    echo ""
    echo -e "${RED}✗ Some DNS tests failed${NC}"
    echo ""
    echo -e "${YELLOW}Troubleshooting tips:${NC}"
    echo "1. Check DNS records at your registrar"
    echo "2. Wait for DNS propagation (can take 1-24 hours)"
    echo "3. Flush local DNS cache: sudo systemd-resolve --flush-caches"
    echo "4. Check online: https://dnschecker.org"
    exit 1
fi
