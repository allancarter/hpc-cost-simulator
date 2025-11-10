# Parallel Processing of Jobs.csv Files

This document describes the new parallel processing capabilities added to JobAnalyzer to handle multiple jobs.csv files efficiently.

## Prerequisites

Before running any JobAnalyzer commands, you must source the `setup.sh` script to activate the Python virtual environment:

```bash
source setup.sh
```

This creates and activates the necessary Python environment with all required dependencies. You need to do this once per shell session.

**Note:** The helper script `parallel_jobs_processor.sh` automatically sources `setup.sh`, so you don't need to do it manually when using that script.

## Overview

The JobAnalyzer has been enhanced to support parallel processing of multiple jobs.csv files. This is useful when you have a large dataset split across multiple CSV files or when you want to process different time periods or job sets independently.

### Scalability Considerations

**For hundreds of input files**: Use HPC job arrays (SLURM/LSF) where each job processes one file independently. This is the **recommended approach** for large-scale processing. See the "Processing on HPC Clusters" section below.

**For a small number of files** (< 20): Use the built-in `parallel_jobs_csv` mode which uses Python multiprocessing on a single node.

**Workflow for large datasets**:
1. Generate an HPC array job script using `generate_slurm_array.sh` or `generate_lsf_array.sh`
2. Submit the array job (each task processes one jobs.csv file)
3. After all jobs complete, run the combine script to merge results and generate statistics

## New Features

### 1. Process Single jobs.csv File (`process_jobs_csv`)

Process a single jobs.csv file and create hourly bucket files without combining them yet.

**Usage:**
```bash
./JobAnalyzer.py --config config.yml --output-dir output process_jobs_csv \
  --input-jobs-csv /path/to/jobs.csv \
  --output-subdir batch_name
```

**Arguments:**
- `--input-jobs-csv`: Path to the jobs.csv file to process (required)
- `--output-subdir`: Subdirectory name for hourly files. If not specified, uses the basename of the input file (optional)

**Output:**
- Hourly bucket files in `output/hourly-files/<output-subdir>/`

### 2. Process Multiple jobs.csv Files in Parallel (`parallel_jobs_csv`)

Process multiple jobs.csv files in parallel, combine the results, and generate final statistics.

**Usage:**
```bash
./JobAnalyzer.py --config config.yml --output-dir output parallel_jobs_csv \
  --jobs-csv-dir /path/to/csv/directory \
  --jobs-csv-pattern "jobs_*.csv" \
  --num-processes 8
```

**Arguments:**
- `--jobs-csv-dir`: Directory containing jobs.csv files to process (required)
- `--jobs-csv-pattern`: Glob pattern for CSV files, e.g., `"*.csv"` or `"jobs_*.csv"` (default: `"*.csv"`)
- `--num-processes`: Number of parallel processes. Defaults to number of CPUs (optional)

**Output:**
- Individual hourly bucket files in `output/hourly-files/batch_NNNN_<filename>/`
- Combined hourly files in `output/hourly-files/`
- Final statistics in `output/hourly_stats.csv` and `output/hourly_stats.xlsx`

### 3. Combine Hourly Files (`combine_hourly`)

Combine hourly files from multiple batch subdirectories into a single set of hourly files. This is useful if you've already processed files individually and want to merge them.

**Usage:**
```bash
./JobAnalyzer.py --config config.yml --output-dir output combine_hourly \
  --batch-subdirs batch_0000_jobs1 batch_0001_jobs2 batch_0002_jobs3
```

**Arguments:**
- `--batch-subdirs`: List of subdirectory names to combine. If not specified, auto-discovers all subdirectories (optional)

**Output:**
- Combined hourly files in `output/hourly-files/`

## Quick Start for Large-Scale Processing (Hundreds of Files)

### SLURM Example

```bash
# Generate SLURM array job script
./generate_slurm_array.sh --jobs-csv-dir /path/to/csvs --output-script process_all.sh

# Submit the array job
JOB_ID=$(sbatch --parsable process_all.sh)

# Submit combine job with dependency
sbatch --dependency=afterok:$JOB_ID combine_and_stats.sh
```

### LSF Example

```bash
# Generate LSF array job script
./generate_lsf_array.sh --jobs-csv-dir /path/to/csvs --output-script process_all_lsf.sh

# Submit the array job
bsub < process_all_lsf.sh
# Note the job ID from output, e.g., Job <12345>

# Submit combine job with dependency
bsub -w 'done(12345)' < combine_and_stats_lsf.sh
```

This approach scales to hundreds or thousands of files and is the **recommended method** for large datasets.

## Workflow Examples

### Example 1: Simple Parallel Processing (Small Number of Files)

Process all CSV files in a directory in parallel:

```bash
source setup.sh
./JobAnalyzer.py --config config.yml --output-dir output parallel_jobs_csv \
  --jobs-csv-dir /data/job_csvs
```

This will:
1. Find all `*.csv` files in `/data/job_csvs`
2. Process each file in parallel (using all available CPUs)
3. Combine the hourly files
4. Generate the final statistics

### Example 2: Controlled Parallel Processing

Process specific CSV files with a limited number of processes:

```bash
source setup.sh
./JobAnalyzer.py --config config.yml --output-dir output parallel_jobs_csv \
  --jobs-csv-dir /data/job_csvs \
  --jobs-csv-pattern "jobs_202401*.csv" \
  --num-processes 4
```

### Example 3: Two-Step Processing

**Step 1:** Process files individually (can be done in separate jobs or manually):

```bash
source setup.sh
./JobAnalyzer.py --config config.yml --output-dir output process_jobs_csv \
  --input-jobs-csv /data/jobs_part1.csv --output-subdir part1

./JobAnalyzer.py --config config.yml --output-dir output process_jobs_csv \
  --input-jobs-csv /data/jobs_part2.csv --output-subdir part2

./JobAnalyzer.py --config config.yml --output-dir output process_jobs_csv \
  --input-jobs-csv /data/jobs_part3.csv --output-subdir part3
```

**Step 2:** Combine the results:

```bash
# Auto-discover all subdirectories
./JobAnalyzer.py --config config.yml --output-dir output combine_hourly

# Or specify subdirectories explicitly
./JobAnalyzer.py --config config.yml --output-dir output combine_hourly \
  --batch-subdirs part1 part2 part3
```

**Step 3:** Process combined hourly files to generate statistics:

```bash
./JobAnalyzer.py --config config.yml --output-dir output hourly_stats
```

### Example 4: Using the Helper Script

A convenience script is provided for easier parallel processing:

```bash
./parallel_jobs_processor.sh --jobs-csv-dir /data/job_csvs --output-dir output
```

With options:

```bash
./parallel_jobs_processor.sh \
  --jobs-csv-dir /data/job_csvs \
  --output-dir output \
  --jobs-csv-pattern "jobs_*.csv" \
  --num-processes 8 \
  --starttime 2024-01-01T00:00:00 \
  --endtime 2024-12-31T23:59:59
```

## Filter Options

All parallel processing modes support the standard filter options:

- `--starttime`: Select jobs after the specified time (Format: `YYYY-MM-DDTHH:MM:SS`)
- `--endtime`: Select jobs before the specified time (Format: `YYYY-MM-DDTHH:MM:SS`)
- `--queues`: Comma-separated list of queue filters (prefix with `-` to exclude)
- `--projects`: Comma-separated list of project filters (prefix with `-` to exclude)

**Example with filters:**

```bash
source setup.sh
./JobAnalyzer.py --config config.yml --output-dir output \
  --starttime 2024-01-01T00:00:00 \
  --endtime 2024-12-31T23:59:59 \
  --queues "prod,test,-debug" \
  parallel_jobs_csv --jobs-csv-dir /data/job_csvs
```

## Architecture

### Directory Structure

```
output/
├── hourly-files/
│   ├── batch_0000_jobs1/
│   │   ├── hourly-1234567.csv
│   │   ├── hourly-1234568.csv
│   │   └── ...
│   ├── batch_0001_jobs2/
│   │   ├── hourly-1234567.csv
│   │   ├── hourly-1234569.csv
│   │   └── ...
│   ├── hourly-1234567.csv  (combined)
│   ├── hourly-1234568.csv  (combined)
│   └── ...
├── hourly_stats.csv
├── hourly_stats.xlsx
└── summary_stats.csv
```

### Processing Flow

1. **Individual Processing Phase:**
   - Each jobs.csv file is processed independently
   - Jobs are analyzed and assigned instance types
   - Hourly bucket files are created in separate subdirectories
   
2. **Combining Phase:**
   - Hourly files with the same hour number are merged
   - Combined files are written to the main hourly-files directory
   
3. **Statistics Generation Phase:**
   - Combined hourly files are processed
   - Final statistics and Excel workbook are generated

## Performance Considerations

- **Memory**: Each parallel process requires memory to load the EC2 instance type information and process jobs. Monitor memory usage when using many parallel processes.

- **CPU**: By default, the number of processes equals the number of CPUs. Reduce this if you have memory constraints.

- **I/O**: The combining phase involves reading/writing many files. Consider using local storage rather than network storage for better performance.

- **Job File Batch Size**: The `job_file_batch_size` configuration parameter controls how many jobs are buffered before writing to hourly files. Larger values use more memory but reduce I/O operations.

## Troubleshooting

### Issue: Out of Memory

**Solution:** Reduce the number of parallel processes:
```bash
--num-processes 2
```

### Issue: CSV Files Not Found

**Solution:** Check the glob pattern and directory:
```bash
# List files that match the pattern
ls /path/to/csv/directory/*.csv

# Adjust the pattern
--jobs-csv-pattern "jobs_*.csv"
```

### Issue: Combining Takes Too Long

**Solution:** This is expected with many hourly files. The process is I/O bound. Consider:
- Using faster storage (SSD vs HDD)
- Processing fewer files at once
- Pre-filtering jobs by time range

### Issue: Duplicate Job IDs

**Solution:** If the same jobs appear in multiple CSV files, they will be counted multiple times. Ensure your CSV files contain unique jobs or filter by time range appropriately.

## Advanced Usage

### Processing on HPC Clusters (Recommended for 100+ Files)

For large-scale processing with hundreds or thousands of files, use HPC job arrays. Helper scripts are provided to generate the necessary job scripts.

#### Using SLURM

**Step 1: Generate the job scripts**

```bash
./generate_slurm_array.sh \
  --jobs-csv-dir /path/to/csvs \
  --output-script process_all.sh \
  --cpus-per-task 1 \
  --mem-per-task 8G \
  --time 4:00:00 \
  --partition normal
```

This creates two scripts:
- `process_all.sh` - Array job to process all CSV files
- `combine_and_stats.sh` - Job to combine results and generate statistics

**Step 2: Submit the array job**

```bash
# Submit and capture job ID
JOB_ID=$(sbatch --parsable process_all.sh)
echo "Submitted array job: $JOB_ID"

# Submit combine job that waits for array job to complete
sbatch --dependency=afterok:$JOB_ID combine_and_stats.sh
```

**Optional: Monitor progress**

```bash
# Check job status
squeue -u $USER

# Check specific array job
squeue -j $JOB_ID

# View output logs
tail -f logs/job_${JOB_ID}_*.out
```

#### Using LSF

**Step 1: Generate the job scripts**

```bash
./generate_lsf_array.sh \
  --jobs-csv-dir /path/to/csvs \
  --output-script process_all_lsf.sh \
  --cpus-per-task 1 \
  --mem-per-task 8192 \
  --time 240 \
  --queue normal
```

This creates two scripts:
- `process_all_lsf.sh` - Array job to process all CSV files
- `combine_and_stats_lsf.sh` - Job to combine results and generate statistics

**Step 2: Submit the array job**

```bash
# Submit array job
bsub < process_all_lsf.sh
# Output will show: Job <12345> is submitted...
# Note the job ID (e.g., 12345)

# Submit combine job with dependency (replace 12345 with your job ID)
bsub -w 'done(12345)' < combine_and_stats_lsf.sh
```

**Optional: Monitor progress**

```bash
# Check job status
bjobs -u $USER

# Check specific array job
bjobs -l 12345

# View output logs
tail -f logs/job_12345_*.out
```

#### Generator Script Options

Both `generate_slurm_array.sh` and `generate_lsf_array.sh` support the same filtering options:

```bash
./generate_slurm_array.sh \
  --jobs-csv-dir /path/to/csvs \
  --jobs-csv-pattern "jobs_2024*.csv" \
  --starttime 2024-01-01T00:00:00 \
  --endtime 2024-12-31T23:59:59 \
  --queues "prod,test,-debug" \
  --projects "project1,project2" \
  --output-dir results \
  --output-script process_filtered.sh
```

#### Advantages of HPC Array Jobs

1. **Scalability**: Process hundreds or thousands of files in parallel
2. **Resource Management**: Scheduler handles resource allocation and queuing
3. **Fault Tolerance**: Individual job failures don't affect others
4. **Monitoring**: Standard HPC monitoring tools work out of the box
5. **Job Dependencies**: Automatic job chaining ensures combine runs after all processing completes
6. **Logging**: Separate log files for each array task for easy debugging

### Custom Batch Naming

You can control the subdirectory naming by using the `--output-subdir` parameter:

```bash
./JobAnalyzer.py --config config.yml --output-dir output process_jobs_csv \
  --input-jobs-csv jobs_2024_q1.csv --output-subdir 2024_q1
```

## Summary

The parallel processing capability allows you to:

1. **Scale**: Process large datasets by splitting them across multiple workers
2. **Flexibility**: Process files independently and combine later
3. **Efficiency**: Utilize multiple CPU cores to reduce total processing time
4. **Control**: Choose between automatic parallel processing or manual step-by-step processing

For most use cases, the `parallel_jobs_csv` mode provides the simplest solution. For more complex scenarios or HPC environments, use the two-step approach with `process_jobs_csv` followed by `combine_hourly`.
