#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

################################################################################
# Script to run JobAnalyzer integration tests with time filtering
#
# This script tests jobs that start before starttime and end after endtime
# using the actual JobAnalyzer.py class (not mocks).
#
# Prerequisites:
#   - Must source setup.sh first to create virtual environment
#   - All Python dependencies must be installed
#
# Usage:
#   cd /path/to/hpc-cost-simulator
#   source setup.sh
#   ./tests/run_integration_tests.sh
################################################################################

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}JobAnalyzer Integration Tests${NC}"
echo -e "${BLUE}Testing Time Filtering for Jobs${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if we're in the correct directory
if [ ! -f "$REPO_DIR/JobAnalyzer.py" ]; then
    echo -e "${RED}Error: Cannot find JobAnalyzer.py${NC}"
    echo -e "${RED}Please run this script from the hpc-cost-simulator directory${NC}"
    exit 1
fi

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}Warning: Python virtual environment is not activated${NC}"
    echo ""
    echo -e "${YELLOW}Please run the following commands first:${NC}"
    echo -e "  cd $REPO_DIR"
    echo -e "  source setup.sh"
    echo ""
    echo -e "${YELLOW}Then run this script again:${NC}"
    echo -e "  ./tests/run_integration_tests.sh"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓ Virtual environment detected: $VIRTUAL_ENV${NC}"
echo ""

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 command not found${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓ Using Python $PYTHON_VERSION${NC}"
echo ""

# Check if required packages are installed
echo "Checking for required Python packages..."
MISSING_PACKAGES=()

for package in unittest yaml; do
    if ! python3 -c "import $package" 2>/dev/null; then
        MISSING_PACKAGES+=($package)
    fi
done

if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    echo -e "${RED}Error: Missing required Python packages: ${MISSING_PACKAGES[*]}${NC}"
    echo -e "${YELLOW}Please run: source setup.sh${NC}"
    exit 1
fi

echo -e "${GREEN}✓ All required packages are installed${NC}"
echo ""

# Change to the repository directory
cd "$REPO_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Running Integration Tests${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Run the integration tests
echo -e "${YELLOW}Test Suite: JobAnalyzer Integration Tests${NC}"
echo -e "${YELLOW}Testing jobs that span time boundaries:${NC}"
echo "  - Jobs starting before starttime"
echo "  - Jobs ending after endtime"
echo "  - Jobs spanning the entire time window"
echo ""

# Run with verbose output
if python3 -m unittest tests.test_job_analyzer_integration -v; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ All Integration Tests Passed!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "Summary:"
    echo "  - Time filtering logic is working correctly"
    echo "  - Jobs spanning time boundaries are handled properly"
    echo "  - Hourly stats are calculated accurately"
    echo ""
    exit 0
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}✗ Some Tests Failed${NC}"
    echo -e "${RED}========================================${NC}"
    echo ""
    exit 1
fi
