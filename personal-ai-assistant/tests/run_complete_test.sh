#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  GMAIL INTEGRATION END-TO-END TEST${NC}"
echo -e "${CYAN}========================================${NC}"

# Check if server is running
echo -e "\n${CYAN}Checking if Flask server is running...${NC}"
if ! curl -s http://localhost:8080/ > /dev/null; then
    echo -e "${RED}Error: Flask server is not running${NC}"
    echo -e "${YELLOW}Please start the server with:${NC}"
    echo -e "  python3 -m backend.main"
    exit 1
fi
echo -e "${GREEN}✓ Flask server is running${NC}"

# Create test_reports directory if it doesn't exist
mkdir -p test_reports

# Run the complete Gmail integration test
echo -e "\n${CYAN}Running complete Gmail integration test...${NC}"
python3 complete_gmail_test.py

# Check if the test was successful
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✓ Complete Gmail integration test passed!${NC}"
else
    echo -e "\n${RED}✗ Complete Gmail integration test failed${NC}"
    echo -e "${YELLOW}Check the test report for details${NC}"
fi

# Find the latest test report
LATEST_REPORT=$(ls -t test_reports/complete_test_*.json | head -1)
if [ -n "$LATEST_REPORT" ]; then
    echo -e "\n${CYAN}Latest test report: ${LATEST_REPORT}${NC}"
fi

echo -e "\n${CYAN}========================================${NC}"
echo -e "${CYAN}  TEST COMPLETE${NC}"
echo -e "${CYAN}========================================${NC}"
