#!/bin/bash
# Generate LSF array job script for processing multiple jobs.csv files
# This is the recommended approach for processing hundreds of files

usage() {
    cat << EOF
Usage: $0 --jobs-csv-dir DIRECTORY [OPTIONS]

Generate an LSF array job script to process multiple jobs.csv files in parallel.

Required Arguments:
  --jobs-csv-dir DIR        Directory containing jobs.csv files to process

Optional Arguments:
  --config FILE             Configuration file (default: config.yml)
  --output-dir DIR          Output directory (default: output)
  --jobs-csv-pattern PATTERN  Glob pattern for CSV files (default: *.csv)
  --cpus-per-task N         CPUs per task (default: 1)
  --mem-per-task MEM        Memory per task in MB (default: 8192)
  --time LIMIT              Time limit per job in minutes (default: 240)
  --queue QUEUE             LSF queue to use (optional)
  --starttime TIME          Select jobs after the specified time (Format: YYYY-MM-DDTHH:MM:SS)
  --endtime TIME            Select jobs before the specified time (Format: YYYY-MM-DDTHH:MM:SS)
  --queues FILTERS          Comma separated list of queue filters
  --projects FILTERS        Comma separated list of project filters
  --output-script FILE      Output script filename (default: run_parallel_jobs_lsf.sh)
  --help                    Show this help message

Example:
  $0 --jobs-csv-dir /path/to/csvs --output-script process_jobs_lsf.sh
  # Then submit:
  bsub < process_jobs_lsf.sh

EOF
    exit 1
}

# Default values
CONFIG_FILE="config.yml"
OUTPUT_DIR="output"
JOBS_CSV_PATTERN="*.csv"
CPUS_PER_TASK=1
MEM_PER_TASK=8192
TIME_LIMIT=240
QUEUE=""
STARTTIME=""
ENDTIME=""
QUEUES=""
PROJECTS=""
OUTPUT_SCRIPT="run_parallel_jobs_lsf.sh"

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
        --cpus-per-task)
            CPUS_PER_TASK="$2"
            shift 2
            ;;
        --mem-per-task)
            MEM_PER_TASK="$2"
            shift 2
            ;;
        --time)
            TIME_LIMIT="$2"
            shift 2
            ;;
        --queue)
            QUEUE="$2"
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
        --output-script)
            OUTPUT_SCRIPT="$2"
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

# Get absolute path of the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Find CSV files
CSV_FILES=($JOBS_CSV_DIR/$JOBS_CSV_PATTERN)
NUM_FILES=${#CSV_FILES[@]}

if [ $NUM_FILES -eq 0 ]; then
    echo "Error: No CSV files found matching pattern $JOBS_CSV_PATTERN in $JOBS_CSV_DIR"
    exit 1
fi

echo "Found $NUM_FILES CSV files to process"
echo "Generating LSF array job script: $OUTPUT_SCRIPT"

# Build JobAnalyzer command
JA_CMD="./JobAnalyzer.py --config $CONFIG_FILE --output-dir $OUTPUT_DIR"

if [ -n "$STARTTIME" ]; then
    JA_CMD="$JA_CMD --starttime $STARTTIME"
fi

if [ -n "$ENDTIME" ]; then
    JA_CMD="$JA_CMD --endtime $ENDTIME"
fi

if [ -n "$QUEUES" ]; then
    JA_CMD="$JA_CMD --queues \"$QUEUES\""
fi

if [ -n "$PROJECTS" ]; then
    JA_CMD="$JA_CMD --projects \"$PROJECTS\""
fi

# Generate the LSF script
cat > "$OUTPUT_SCRIPT" << EOF
#!/bin/bash
#BSUB -J process_jobs[1-$NUM_FILES]
#BSUB -n $CPUS_PER_TASK
#BSUB -M $MEM_PER_TASK
#BSUB -W $TIME_LIMIT
#BSUB -o logs/job_%J_%I.out
#BSUB -e logs/job_%J_%I.err
EOF

if [ -n "$QUEUE" ]; then
    cat >> "$OUTPUT_SCRIPT" << EOF
#BSUB -q $QUEUE
EOF
fi

cat >> "$OUTPUT_SCRIPT" << EOF

# Array of CSV files to process
CSV_FILES=(
EOF

# Add each CSV file to the array
for csv_file in "${CSV_FILES[@]}"; do
    echo "    \"$csv_file\"" >> "$OUTPUT_SCRIPT"
done

cat >> "$OUTPUT_SCRIPT" << EOF
)

# Get the CSV file for this array task (LSB_JOBINDEX is 1-based)
CSV_FILE="\${CSV_FILES[\$((LSB_JOBINDEX - 1))]}"
CSV_BASENAME=\$(basename "\$CSV_FILE" .csv)
BATCH_SUBDIR="batch_\$(printf "%04d" \$((LSB_JOBINDEX - 1)))_\${CSV_BASENAME}"

echo "=================================================="
echo "LSF Array Job: \$LSB_JOBID"
echo "Array Task Index: \$LSB_JOBINDEX"
echo "Processing: \$CSV_FILE"
echo "Output subdir: \$BATCH_SUBDIR"
echo "=================================================="

# Change to script directory
cd $SCRIPT_DIR

# Source the Python virtual environment
source setup.sh

# Create logs directory if it doesn't exist
mkdir -p logs

# Process the CSV file
$JA_CMD process_jobs_csv \\
    --input-jobs-csv "\$CSV_FILE" \\
    --output-subdir "\$BATCH_SUBDIR"

EXIT_CODE=\$?

if [ \$EXIT_CODE -eq 0 ]; then
    echo "Successfully processed \$CSV_FILE"
else
    echo "ERROR: Failed to process \$CSV_FILE (exit code: \$EXIT_CODE)"
    exit \$EXIT_CODE
fi
EOF

chmod +x "$OUTPUT_SCRIPT"

# Also generate a combine script
COMBINE_SCRIPT="combine_and_stats_lsf.sh"

cat > "$COMBINE_SCRIPT" << EOF
#!/bin/bash
#BSUB -J combine_stats
#BSUB -n 1
#BSUB -M 16384
#BSUB -W 120
#BSUB -o logs/combine_%J.out
#BSUB -e logs/combine_%J.err
EOF

if [ -n "$QUEUE" ]; then
    cat >> "$COMBINE_SCRIPT" << EOF
#BSUB -q $QUEUE
EOF
fi

cat >> "$COMBINE_SCRIPT" << EOF

echo "=================================================="
echo "Combining hourly files and generating statistics"
echo "=================================================="

# Change to script directory
cd $SCRIPT_DIR

# Source the Python virtual environment
source setup.sh

# Create logs directory if it doesn't exist
mkdir -p logs

# Combine hourly files
echo "Step 1: Combining hourly files..."
./JobAnalyzer.py --config $CONFIG_FILE --output-dir $OUTPUT_DIR combine_hourly

if [ \$? -ne 0 ]; then
    echo "ERROR: Failed to combine hourly files"
    exit 1
fi

# Generate statistics
echo "Step 2: Generating statistics..."
./JobAnalyzer.py --config $CONFIG_FILE --output-dir $OUTPUT_DIR hourly_stats

if [ \$? -eq 0 ]; then
    echo "Successfully generated statistics"
    echo "Results are in: $OUTPUT_DIR"
else
    echo "ERROR: Failed to generate statistics"
    exit 1
fi
EOF

chmod +x "$COMBINE_SCRIPT"

echo ""
echo "Generated scripts:"
echo "  1. $OUTPUT_SCRIPT - Process $NUM_FILES CSV files"
echo "  2. $COMBINE_SCRIPT - Combine results and generate statistics"
echo ""
echo "To run:"
echo "  # Submit array job to process all files"
echo "  bsub < $OUTPUT_SCRIPT"
echo "  # Note the job ID from the output, e.g., Job <12345>"
echo ""
echo "  # Submit combine job with dependency"
echo "  bsub -w 'done(12345)' < $COMBINE_SCRIPT"
echo ""
echo "Or manually:"
echo "  bsub < $OUTPUT_SCRIPT"
echo "  # Wait for all jobs to complete (check with bjobs), then:"
echo "  bsub < $COMBINE_SCRIPT"
echo ""
