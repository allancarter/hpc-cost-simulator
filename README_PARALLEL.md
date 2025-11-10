# Parallel Processing Guide - Quick Reference

This guide helps you process hundreds of jobs.csv files efficiently using HPC job arrays.

## Intended Use Case

You have **hundreds of jobs.csv files** and need to process them in parallel on an HPC cluster (SLURM or LSF).

## Three-Step Workflow

### Step 1: Generate Job Scripts

Choose your scheduler:

**For SLURM:**
```bash
./generate_slurm_array.sh --jobs-csv-dir /path/to/your/csv/files
```

**For LSF:**
```bash
./generate_lsf_array.sh --jobs-csv-dir /path/to/your/csv/files
```

This creates:
- An array job script to process all files (one job per file)
- A combine script to merge results and generate statistics

### Step 2: Submit Array Job

**For SLURM:**
```bash
# Submit array job
JOB_ID=$(sbatch --parsable run_parallel_jobs.sh)

# Submit combine job (waits for array job to finish)
sbatch --dependency=afterok:$JOB_ID combine_and_stats.sh
```

**For LSF:**
```bash
# Submit array job
bsub < run_parallel_jobs_lsf.sh
# Output: Job <12345> is submitted...

# Submit combine job (replace 12345 with your job ID)
bsub -w 'done(12345)' < combine_and_stats_lsf.sh
```

### Step 3: Monitor & Collect Results

**Monitor jobs:**
```bash
# SLURM
squeue -u $USER

# LSF
bjobs -u $USER
```

**View logs:**
```bash
# Individual processing jobs
tail -f logs/job_*_*.out

# Combine job
tail -f logs/combine_*.out
```

**Results location:**
```
output/
├── hourly_stats.csv        ← Final cost statistics (CSV)
├── hourly_stats.xlsx       ← Final cost statistics (Excel)
└── summary_stats.csv       ← Summary statistics
```

## Common Options

### Filter by Time Range

```bash
./generate_slurm_array.sh \
  --jobs-csv-dir /path/to/csvs \
  --starttime 2024-01-01T00:00:00 \
  --endtime 2024-12-31T23:59:59
```

### Filter by Queue or Project

```bash
./generate_slurm_array.sh \
  --jobs-csv-dir /path/to/csvs \
  --queues "prod,test,-debug" \
  --projects "project1,project2"
```

### Adjust Resources

```bash
./generate_slurm_array.sh \
  --jobs-csv-dir /path/to/csvs \
  --cpus-per-task 2 \
  --mem-per-task 16G \
  --time 8:00:00 \
  --partition high_mem
```

### Process Specific Files

```bash
./generate_slurm_array.sh \
  --jobs-csv-dir /path/to/csvs \
  --jobs-csv-pattern "jobs_2024*.csv"
```

## How It Works

```
Input: 
  /path/to/csvs/
    ├── jobs_batch_001.csv
    ├── jobs_batch_002.csv
    ├── ...
    └── jobs_batch_300.csv

Processing (each file = one HPC job):
  Job 1: jobs_batch_001.csv → output/hourly-files/batch_0000_jobs_batch_001/
  Job 2: jobs_batch_002.csv → output/hourly-files/batch_0001_jobs_batch_002/
  ...
  Job 300: jobs_batch_300.csv → output/hourly-files/batch_0299_jobs_batch_300/

Combining:
  All batch_*/hourly-*.csv → output/hourly-files/hourly-*.csv (merged)

Statistics:
  output/hourly-files/hourly-*.csv → output/hourly_stats.csv
                                   → output/hourly_stats.xlsx
```

## Troubleshooting

### Issue: No CSV files found

**Check:**
```bash
ls /path/to/csvs/*.csv
```

**Solution:** Verify the directory path and use `--jobs-csv-pattern` if needed.

### Issue: Job failed for one file

**Find the failed job:**
```bash
# SLURM
grep -l "ERROR" logs/job_*_*.err

# LSF
grep -l "ERROR" logs/job_*_*.err
```

**Reprocess that file manually:**
```bash
source setup.sh
./JobAnalyzer.py --config config.yml --output-dir output process_jobs_csv \
  --input-jobs-csv /path/to/failed_file.csv \
  --output-subdir batch_XXXX_failed_file
```

Then re-run combine:
```bash
sbatch combine_and_stats.sh   # SLURM
# or
bsub < combine_and_stats_lsf.sh   # LSF
```

### Issue: Out of memory

**Solution:** Increase memory in generator script:
```bash
./generate_slurm_array.sh \
  --jobs-csv-dir /path/to/csvs \
  --mem-per-task 16G
```

### Issue: Jobs taking too long

**Solution:** Increase time limit:
```bash
./generate_slurm_array.sh \
  --jobs-csv-dir /path/to/csvs \
  --time 8:00:00
```

## Alternative: Manual Processing (Not Recommended for 100+ Files)

For small numbers of files (< 20), you can use built-in multiprocessing:

```bash
source setup.sh
./JobAnalyzer.py --config config.yml --output-dir output parallel_jobs_csv \
  --jobs-csv-dir /path/to/csvs --num-processes 8
```

Or use the helper script:

```bash
./parallel_jobs_processor.sh --jobs-csv-dir /path/to/csvs --output-dir output
```

**Note:** This runs on a single node and doesn't scale well beyond 20 files.

## For More Information

- **Comprehensive guide:** `PARALLEL_PROCESSING.md`
- **Summary document:** `PARALLEL_PROCESSING_SUMMARY.md`
- **Generator script help:**
  ```bash
  ./generate_slurm_array.sh --help
  ./generate_lsf_array.sh --help
  ```

## Prerequisites

Make sure `setup.sh` exists in the hpc-cost-simulator directory. The generated scripts will automatically source it to activate the Python environment.

## Quick Example: Complete Workflow

```bash
# 1. Generate scripts
./generate_slurm_array.sh --jobs-csv-dir /data/job_csvs

# 2. Submit jobs
JOB_ID=$(sbatch --parsable run_parallel_jobs.sh)
sbatch --dependency=afterok:$JOB_ID combine_and_stats.sh

# 3. Monitor
watch squeue -u $USER

# 4. View results (after completion)
ls -lh output/hourly_stats.*
```

That's it! The HPC scheduler handles everything else.
