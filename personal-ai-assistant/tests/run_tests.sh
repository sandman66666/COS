#!/bin/bash
# End-to-End Test Runner for Gmail Integration
# This script runs the test suite and generates a report

# Set up colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=========================================${NC}"
echo -e "${YELLOW}  Gmail Integration End-to-End Tests     ${NC}"
echo -e "${YELLOW}=========================================${NC}"

# Check if server is running
if ! curl -s http://localhost:8080 > /dev/null; then
  echo -e "${RED}Error: Flask server is not running${NC}"
  echo "Please start the server with: python -m backend.main"
  exit 1
fi

# Create test directory if it doesn't exist
mkdir -p test_reports

# Run the tests and capture output
echo "Running tests..."
TEST_OUTPUT=$(python tests/test_gmail_integration.py 2>&1)
TEST_STATUS=$?

# Save test output to file
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUTPUT_FILE="test_reports/gmail_integration_test_${TIMESTAMP}.log"
echo "$TEST_OUTPUT" > "$OUTPUT_FILE"

echo -e "${YELLOW}----------------------------------------${NC}"
echo -e "${YELLOW}            Test Summary               ${NC}"
echo -e "${YELLOW}----------------------------------------${NC}"

# Extract and display test results
PASSED=$(echo "$TEST_OUTPUT" | grep -c "successful")
FAILED=$(echo "$TEST_OUTPUT" | grep -c "FAIL")
ERRORS=$(echo "$TEST_OUTPUT" | grep -c "ERROR")
WARNINGS=$(echo "$TEST_OUTPUT" | grep -c "WARNING")

echo -e "Tests passed: ${GREEN}$PASSED${NC}"
if [ $FAILED -gt 0 ]; then
  echo -e "Tests failed: ${RED}$FAILED${NC}"
  echo -e "${RED}Failed tests:${NC}"
  echo "$TEST_OUTPUT" | grep -A 1 "FAIL" | grep -v "^--$"
fi

if [ $ERRORS -gt 0 ]; then
  echo -e "Errors: ${RED}$ERRORS${NC}"
  echo -e "${RED}Error details:${NC}"
  echo "$TEST_OUTPUT" | grep -A 2 "ERROR" | grep -v "^--$"
fi

if [ $WARNINGS -gt 0 ]; then
  echo -e "Warnings: ${YELLOW}$WARNINGS${NC}"
  echo -e "${YELLOW}Warning details:${NC}"
  echo "$TEST_OUTPUT" | grep -A 1 "WARNING" | grep -v "^--$"
fi

echo -e "${YELLOW}----------------------------------------${NC}"
echo "Full test log saved to: $OUTPUT_FILE"

# Check API endpoints manually
echo -e "${YELLOW}----------------------------------------${NC}"
echo -e "${YELLOW}       API Endpoint Status Check        ${NC}"
echo -e "${YELLOW}----------------------------------------${NC}"

check_endpoint() {
  local endpoint=$1
  local method=${2:-GET}
  local status_code
  
  if [ "$method" = "GET" ]; then
    status_code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:5000$endpoint")
  else
    status_code=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" "http://localhost:5000$endpoint")
  fi
  
  if [ "$status_code" = "200" ]; then
    echo -e "$endpoint: ${GREEN}OK ($status_code)${NC}"
  else
    echo -e "$endpoint: ${RED}FAIL ($status_code)${NC}"
  fi
}

# Check critical endpoints
check_endpoint "/api/people"
check_endpoint "/api/tasks"
check_endpoint "/api/insights"
check_endpoint "/api/debug-gmail"
check_endpoint "/api/integrations/status"
check_endpoint "/api/sync-status"
check_endpoint "/api/reset-database" "POST"

echo -e "${YELLOW}=========================================${NC}"
if [ $TEST_STATUS -eq 0 ] && [ $FAILED -eq 0 ] && [ $ERRORS -eq 0 ]; then
  echo -e "${GREEN}All tests passed successfully!${NC}"
else
  echo -e "${RED}Tests completed with issues. Please check the log for details.${NC}"
fi
echo -e "${YELLOW}=========================================${NC}"

# Make the script executable
chmod +x "$0"
