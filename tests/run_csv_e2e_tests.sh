#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

################################################################################
# Script to run JobAnalyzer CSV End-to-End tests
#
# This script tests the complete workflow:
#   1. Creates synthetic jobs.csv file
#   2. Runs actual JobAnalyzer.py to process it
#   3. Validates hourly_stats.csv output file
#
# Tests focus on jobs that start before starttime and end after endtime.
#
# Prerequisites:
#   - Must source setup.sh first to create virtual environment
#   - All Python dependencies must be installed
#
# Usage:
#   cd /path/to/hpc-cost-simulator
#   source setup.sh
#   ./tests/run_csv_e2e_tests.sh
################################################################################

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}JobAnalyzer CSV End-to-End Tests${NC}"
echo -e "${BLUE}Complete Workflow Validation${NC}"
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
    echo -e "  ./tests/run_csv_e2e_tests.sh"
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

for package in unittest yaml csv json; do
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
echo -e "${BLUE}Running CSV End-to-End Tests${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo -e "${CYAN}Test Workflow:${NC}"
echo "  1. Create synthetic jobs.csv with test data"
echo "  2. Run actual JobAnalyzer.py to process CSV"
echo "  3. Validate hourly_stats.csv output file"
echo "  4. Verify time filtering is correct"
echo ""

echo -e "${YELLOW}Test Scenarios:${NC}"
echo "  • Job spanning entire time window and beyond"
echo "  • Job starting before, ending within window"
echo "  • Job starting within, ending after window"
echo "  • Multiple jobs with different time relationships"
echo "  • Spot eligible vs long-running jobs"
echo "  • Cost calculation accuracy for partial hours"
echo "  • Jobs completely outside time window"
echo ""

# Run with verbose output
if python3 -m unittest tests.test_job_analyzer_csv_e2e -v; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ All CSV E2E Tests Passed!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${CYAN}Summary:${NC}"
    echo "  ✓ Synthetic CSV files created successfully"
    echo "  ✓ JobAnalyzer processed jobs correctly"
    echo "  ✓ hourly_stats.csv output validated"
    echo "  ✓ Time filtering working as expected"
    echo "  ✓ Cost calculations accurate"
    echo ""
    echo -e "${CYAN}What was tested:${NC}"
    echo "  • Jobs starting BEFORE starttime"
    echo "  • Jobs ending AFTER endtime"
    echo "  • Jobs spanning entire time window"
    echo "  • Partial hour calculations"
    echo "  • CSV input → CSV output workflow"
    echo ""
    exit 0
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}✗ Some Tests Failed${NC}"
    echo -e "${RED}========================================${NC}"
    echo ""
    echo -e "${YELLOW}Debugging tips:${NC}"
    echo "  1. Check test output above for specific errors"
    echo "  2. Verify setup.sh completed successfully"
    echo "  3. Ensure all dependencies are installed"
    echo "  4. Check temporary files in /tmp/ for debugging"
    echo ""
    exit 1
fi
