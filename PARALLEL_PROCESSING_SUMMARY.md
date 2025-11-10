# Parallel Processing Implementation Summary

## Overview
The JobAnalyzer has been enhanced to support parallel processing of multiple jobs.csv files. This allows you to efficiently process large datasets by splitting them across multiple workers.

## What Was Changed

### 1. Modified `JobAnalyzer.py`
Added the following new methods and capabilities:

- **`process_jobs_csv_to_hourly()`**: Process a single jobs.csv file to create hourly bucket files
- **`combine_hourly_files()`**: Merge hourly files from multiple batch subdirectories
- **`process_jobs_csv_parallel()`**: Process multiple jobs.csv files in parallel using multiprocessing
- **`_process_single_csv_worker()`**: Static worker method for parallel processing

Added new command-line parser modes:
- `process_jobs_csv`: Process a single jobs.csv file
- `parallel_jobs_csv`: Process multiple jobs.csv files in parallel
- `combine_hourly`: Combine hourly files from subdirectories

### 2. Created `parallel_jobs_processor.sh`
A convenience shell script that:
- Automatically sources `setup.sh` to activate the Python environment
- Provides a user-friendly interface for parallel processing
- Handles all command-line argument passing

### 3. Created Documentation
- **`PARALLEL_PROCESSING.md`**: Comprehensive documentation covering all new features, examples, and troubleshooting
- **`PARALLEL_PROCESSING_SUMMARY.md`**: This summary file

### 4. Created Test Infrastructure
- **`test_parallel_processing.py`**: Script to generate test data and provide test commands

## Quick Start

### For Large Scale (Hundreds of Files) - RECOMMENDED

Use HPC job arrays for maximum scalability:

**SLURM:**
```bash
./generate_slurm_array.sh --jobs-csv-dir /path/to/csvs
JOB_ID=$(sbatch --parsable run_parallel_jobs.sh)
sbatch --dependency=afterok:$JOB_ID combine_and_stats.sh
```

**LSF:**
```bash
./generate_lsf_array.sh --jobs-csv-dir /path/to/csvs
bsub < run_parallel_jobs_lsf.sh
# Note job ID and submit: bsub -w 'done(JOBID)' < combine_and_stats_lsf.sh
```

This approach:
- Scales to hundreds or thousands of files
- Each file processed as a separate HPC job
- Automatic job dependencies and logging
- Fault-tolerant (individual failures don't stop others)

### For Small Scale (< 20 Files)

Use the built-in multiprocessing for simplicity:

```bash
./parallel_jobs_processor.sh --jobs-csv-dir /path/to/csv/files --output-dir output
```

Or directly:

```bash
source setup.sh
./JobAnalyzer.py --config config.yml --output-dir output parallel_jobs_csv \
  --jobs-csv-dir /path/to/csv/files
```

## Key Benefits

1. **Scalability**: Process large datasets by splitting them across multiple CSV files
2. **Performance**: Utilize multiple CPU cores to reduce processing time
3. **Flexibility**: Choose between automatic parallel processing or manual step-by-step control
4. **Robustness**: Each file is processed independently, so failures don't affect other files

## Architecture

### Processing Flow

```
Phase 1: Individual Processing (Parallel)
├── jobs_batch_1.csv → batch_0000_jobs_batch_1/hourly-*.csv
├── jobs_batch_2.csv → batch_0001_jobs_batch_2/hourly-*.csv
└── jobs_batch_3.csv → batch_0002_jobs_batch_3/hourly-*.csv

Phase 2: Combining
└── All batch subdirectories → hourly-files/hourly-*.csv (combined)

Phase 3: Statistics Generation
└── Combined hourly files → hourly_stats.csv, hourly_stats.xlsx
```

### Directory Structure

```
output/
├── hourly-files/
│   ├── batch_0000_jobs_batch_1/    # Individual batch outputs
│   │   └── hourly-*.csv
│   ├── batch_0001_jobs_batch_2/
│   │   └── hourly-*.csv
│   ├── hourly-*.csv                # Combined outputs
│   └── ...
├── hourly_stats.csv
├── hourly_stats.xlsx
└── summary_stats.csv
```

## Usage Scenarios

### Scenario 1: Simple Parallel Processing
You have multiple jobs.csv files and want to process them all at once.

**Solution**: Use `parallel_jobs_csv` mode
```bash
source setup.sh
./JobAnalyzer.py --config config.yml --output-dir output parallel_jobs_csv \
  --jobs-csv-dir /path/to/csvs
```

### Scenario 2: HPC Cluster Job Array
You want to submit each CSV file as a separate HPC job.

**Solution**: Use `process_jobs_csv` mode in an array job, then combine
```bash
# In SLURM array job
source setup.sh
./JobAnalyzer.py --config config.yml --output-dir output process_jobs_csv \
  --input-jobs-csv ${CSV_FILES[$SLURM_ARRAY_TASK_ID]}

# After all jobs complete
source setup.sh
./JobAnalyzer.py --config config.yml --output-dir output combine_hourly
./JobAnalyzer.py --config config.yml --output-dir output hourly_stats
```

### Scenario 3: Incremental Processing
You want to process files as they become available, then combine later.

**Solution**: Process individually, then combine when ready
```bash
# Process each file as it arrives
source setup.sh
./JobAnalyzer.py --config config.yml --output-dir output process_jobs_csv \
  --input-jobs-csv new_jobs.csv --output-subdir batch_new

# Later, combine all results
./JobAnalyzer.py --config config.yml --output-dir output combine_hourly
```

## Files Created

| File | Purpose |
|------|---------|
| `JobAnalyzer.py` | Modified to add parallel processing capabilities |
| `generate_slurm_array.sh` | Generate SLURM array job scripts (for hundreds of files) |
| `generate_lsf_array.sh` | Generate LSF array job scripts (for hundreds of files) |
| `parallel_jobs_processor.sh` | Helper script for multiprocessing (for small number of files) |
| `PARALLEL_PROCESSING.md` | Comprehensive documentation |
| `PARALLEL_PROCESSING_SUMMARY.md` | This summary |
| `test_parallel_processing.py` | Test data generation script |

## Testing

To test the new functionality:

1. Generate test data:
```bash
python test_parallel_processing.py
```

2. Run the tests using the commands displayed by the script

3. Verify the output files are created correctly

## Important Notes

- **Always source `setup.sh`** before running JobAnalyzer.py (the helper script does this automatically)
- Each parallel worker loads the EC2 instance type information, so memory usage scales with the number of processes
- The combining phase can be I/O intensive with many hourly files
- Files processed in parallel must contain unique jobs to avoid double-counting

## For More Information

See `PARALLEL_PROCESSING.md` for:
- Detailed usage examples
- All command-line options
- Troubleshooting guide
- Advanced usage scenarios
- Performance considerations
