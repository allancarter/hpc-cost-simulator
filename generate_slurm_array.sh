#!/bin/bash
# Generate SLURM array job script for processing multiple jobs.csv files
# This is the recommended approach for processing hundreds of files

usage() {
    cat << EOF
Usage: $0 --jobs-csv-dir DIRECTORY [OPTIONS]

Generate a SLURM array job script to process multiple jobs.csv files in parallel.

Required Arguments:
  --jobs-csv-dir DIR        Directory containing jobs.csv files to process

Optional Arguments:
  --config FILE             Configuration file (default: config.yml)
  --output-dir DIR          Output directory (default: output)
  --jobs-csv-pattern PATTERN  Glob pattern for CSV files (default: *.csv)
  --cpus-per-task N         CPUs per task (default: 1)
  --mem-per-task MEM        Memory per task, e.g., 8G, 16G (default: 8G)
  --time LIMIT              Time limit per job, e.g., 1:00:00 (default: 4:00:00)
  --partition PARTITION     SLURM partition to use (optional)
  --starttime TIME          Select jobs after the specified time (Format: YYYY-MM-DDTHH:MM:SS)
  --endtime TIME            Select jobs before the specified time (Format: YYYY-MM-DDTHH:MM:SS)
  --queues FILTERS          Comma separated list of queue filters
  --projects FILTERS        Comma separated list of project filters
  --output-script FILE      Output script filename (default: run_parallel_jobs.sh)
  --help                    Show this help message

Example:
  $0 --jobs-csv-dir /path/to/csvs --output-script process_jobs.sh
  # Then submit:
  sbatch process_jobs.sh

EOF
    exit 1
}

# Default values
CONFIG_FILE="config.yml"
OUTPUT_DIR="output"
JOBS_CSV_PATTERN="*.csv"
CPUS_PER_TASK=1
MEM_PER_TASK="8G"
TIME_LIMIT="4:00:00"
PARTITION=""
STARTTIME=""
ENDTIME=""
QUEUES=""
PROJECTS=""
OUTPUT_SCRIPT="run_parallel_jobs.sh"

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
        --partition)
            PARTITION="$2"
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
echo "Generating SLURM array job script: $OUTPUT_SCRIPT"

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

# Generate the SLURM script
cat > "$OUTPUT_SCRIPT" << 'EOF_SCRIPT_HEADER'
#!/bin/bash
EOF_SCRIPT_HEADER

cat >> "$OUTPUT_SCRIPT" << EOF
#SBATCH --job-name=process_jobs
#SBATCH --array=0-$((NUM_FILES - 1))
#SBATCH --cpus-per-task=$CPUS_PER_TASK
#SBATCH --mem=$MEM_PER_TASK
#SBATCH --time=$TIME_LIMIT
#SBATCH --output=logs/job_%A_%a.out
#SBATCH --error=logs/job_%A_%a.err
EOF

if [ -n "$PARTITION" ]; then
    cat >> "$OUTPUT_SCRIPT" << EOF
#SBATCH --partition=$PARTITION
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

# Get the CSV file for this array task
CSV_FILE="\${CSV_FILES[\$SLURM_ARRAY_TASK_ID]}"
CSV_BASENAME=\$(basename "\$CSV_FILE" .csv)
BATCH_SUBDIR="batch_\$(printf "%04d" \$SLURM_ARRAY_TASK_ID)_\${CSV_BASENAME}"

echo "=================================================="
echo "SLURM Array Job: \$SLURM_ARRAY_JOB_ID"
echo "Array Task ID: \$SLURM_ARRAY_TASK_ID"
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
COMBINE_SCRIPT="combine_and_stats.sh"

cat > "$COMBINE_SCRIPT" << EOF
#!/bin/bash
#SBATCH --job-name=combine_stats
#SBATCH --cpus-per-task=1
#SBATCH --mem=16G
#SBATCH --time=2:00:00
#SBATCH --output=logs/combine_%j.out
#SBATCH --error=logs/combine_%j.err
EOF

if [ -n "$PARTITION" ]; then
    cat >> "$COMBINE_SCRIPT" << EOF
#SBATCH --partition=$PARTITION
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
echo "  JOB_ID=\$(sbatch --parsable $OUTPUT_SCRIPT)"
echo ""
echo "  # Submit combine job with dependency"
echo "  sbatch --dependency=afterok:\$JOB_ID $COMBINE_SCRIPT"
echo ""
echo "Or manually:"
echo "  sbatch $OUTPUT_SCRIPT"
echo "  # Wait for all jobs to complete, then:"
echo "  sbatch $COMBINE_SCRIPT"
echo ""
