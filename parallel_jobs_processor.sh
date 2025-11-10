#!/bin/bash
# Helper script to process multiple jobs.csv files in parallel
# This script simplifies the process of running the JobAnalyzer in parallel mode

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Source setup.sh to activate the Python virtual environment
if [ -f "$SCRIPT_DIR/setup.sh" ]; then
    source "$SCRIPT_DIR/setup.sh"
else
    echo "Warning: setup.sh not found in $SCRIPT_DIR"
    echo "You may need to source setup.sh manually before running this script"
fi

# Default values
CONFIG_FILE="config.yml"
OUTPUT_DIR="output"
NUM_PROCESSES=""
JOBS_CSV_PATTERN="*.csv"
STARTTIME=""
ENDTIME=""
QUEUES=""
PROJECTS=""

# Usage function
usage() {
    cat << EOF
Usage: $0 --jobs-csv-dir DIRECTORY [OPTIONS]

Process multiple jobs.csv files in parallel using JobAnalyzer.

Required Arguments:
  --jobs-csv-dir DIR        Directory containing jobs.csv files to process

Optional Arguments:
  --config FILE             Configuration file (default: config.yml)
  --output-dir DIR          Output directory (default: output)
  --jobs-csv-pattern PATTERN  Glob pattern for CSV files (default: *.csv)
  --num-processes N         Number of parallel processes (default: number of CPUs)
  --starttime TIME          Select jobs after the specified time (Format: YYYY-MM-DDTHH:MM:SS)
  --endtime TIME            Select jobs before the specified time (Format: YYYY-MM-DDTHH:MM:SS)
  --queues FILTERS          Comma separated list of queue filters
  --projects FILTERS        Comma separated list of project filters
  --help                    Show this help message

Examples:
  # Process all CSV files in a directory
  $0 --jobs-csv-dir /path/to/csv/files --output-dir results

  # Process with specific pattern and 8 processes
  $0 --jobs-csv-dir /path/to/csv/files --jobs-csv-pattern "jobs_*.csv" --num-processes 8

  # Process with time range filter
  $0 --jobs-csv-dir /path/to/csv/files --starttime 2024-01-01T00:00:00 --endtime 2024-12-31T23:59:59

EOF
    exit 1
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --jobs-csv-dir)
            JOBS_CSV_DIR="$2"
            shift 2
            ;;
        --config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --jobs-csv-pattern)
            JOBS_CSV_PATTERN="$2"
            shift 2
            ;;
        --num-processes)
            NUM_PROCESSES="$2"
            shift 2
            ;;
        --starttime)
            STARTTIME="$2"
            shift 2
            ;;
        --endtime)
            ENDTIME="$2"
            shift 2
            ;;
        --queues)
            QUEUES="$2"
            shift 2
            ;;
        --projects)
            PROJECTS="$2"
            shift 2
            ;;
        --help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Check required arguments
if [ -z "$JOBS_CSV_DIR" ]; then
    echo "Error: --jobs-csv-dir is required"
    usage
fi

# Check if directory exists
if [ ! -d "$JOBS_CSV_DIR" ]; then
    echo "Error: Directory not found: $JOBS_CSV_DIR"
    exit 1
fi

# Build the command
CMD="./JobAnalyzer.py --config $CONFIG_FILE --output-dir $OUTPUT_DIR"

# Add optional arguments
if [ -n "$STARTTIME" ]; then
    CMD="$CMD --starttime $STARTTIME"
fi

if [ -n "$ENDTIME" ]; then
    CMD="$CMD --endtime $ENDTIME"
fi

if [ -n "$QUEUES" ]; then
    CMD="$CMD --queues \"$QUEUES\""
fi

if [ -n "$PROJECTS" ]; then
    CMD="$CMD --projects \"$PROJECTS\""
fi

# Add parser-specific arguments
CMD="$CMD parallel_jobs_csv --jobs-csv-dir $JOBS_CSV_DIR --jobs-csv-pattern \"$JOBS_CSV_PATTERN\""

if [ -n "$NUM_PROCESSES" ]; then
    CMD="$CMD --num-processes $NUM_PROCESSES"
fi

# Display the command
echo "Running: $CMD"
echo ""

# Execute the command
eval $CMD

# Check exit status
if [ $? -eq 0 ]; then
    echo ""
    echo "Processing completed successfully!"
    echo "Results are in: $OUTPUT_DIR"
else
    echo ""
    echo "Processing failed with error code: $?"
    exit 1
fi
