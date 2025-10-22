# Quick Start Guide: Running Integration Tests

This guide shows you exactly how to run the JobAnalyzer integration tests that verify time filtering for jobs that span time boundaries.

## Step-by-Step Instructions

### Step 1: Navigate to the Repository

```bash
cd /home/scratch.acarter_gpu/lsf-logs/hpc-cost-simulator
```

### Step 2: Source the Setup Script

This creates a virtual environment and installs all required Python packages:

```bash
source setup.sh
```

**Expected output:**
```
Setting up for RedHat 8

Activating python virtual environment: .venv

Using python 3.x.x

Installing python packages in .venv
...
✓ Setup complete
```

### Step 3: Run the Integration Tests

```bash
./tests/run_integration_tests.sh
```

**Expected output:**
```
========================================
JobAnalyzer Integration Tests
Testing Time Filtering for Jobs
========================================

✓ Virtual environment detected: /home/scratch.acarter_gpu/lsf-logs/hpc-cost-simulator/.venv
✓ Using Python 3.x.x
✓ All required packages are installed

========================================
Running Integration Tests
========================================

test_job_spanning_time_boundaries_with_hourly_files ... ok
test_multiple_jobs_with_different_time_spans ... ok
test_real_job_analyzer_time_filtering ... ok
test_spot_vs_ondemand_with_time_filtering ... ok
test_verify_cost_calculation_accuracy ... ok

----------------------------------------------------------------------
Ran 5 tests in X.XXXs

OK

========================================
✓ All Integration Tests Passed!
========================================
```

## All-in-One Command

For convenience, here's a single command that does everything:

```bash
cd /home/scratch.acarter_gpu/lsf-logs/hpc-cost-simulator && source setup.sh && ./tests/run_integration_tests.sh
```

## What's Being Tested?

These integration tests verify that `JobAnalyzer.py` correctly handles:

1. ✓ Jobs that **start before** the specified `starttime`
2. ✓ Jobs that **end after** the specified `endtime`
3. ✓ Jobs that **span the entire time window** and beyond
4. ✓ Multiple jobs with different time relationships
5. ✓ Spot vs On-Demand instance categorization
6. ✓ Accurate cost calculations for partial hours

## Troubleshooting

### Problem: "Python virtual environment is not activated"

You forgot to run `source setup.sh`

**Fix:**
```bash
source setup.sh
./tests/run_integration_tests.sh
```

### Problem: "command not found: ./tests/run_integration_tests.sh"

You're in the wrong directory.

**Fix:**
```bash
cd /home/scratch.acarter_gpu/lsf-logs/hpc-cost-simulator
./tests/run_integration_tests.sh
```

### Problem: Tests fail with import errors

Dependencies aren't installed properly.

**Fix:**
```bash
rm -rf .venv
source setup.sh
./tests/run_integration_tests.sh
```

## Running Individual Tests

If you want to run just one specific test:

```bash
# After sourcing setup.sh
python3 -m unittest tests.test_job_analyzer_integration.TestJobAnalyzerIntegration.test_job_spanning_time_boundaries_with_hourly_files -v
```

## Understanding the Test Output

Each test name explains what it's testing:

- **`test_real_job_analyzer_time_filtering`**
  - Basic test of time filtering logic with real JobAnalyzer

- **`test_job_spanning_time_boundaries_with_hourly_files`**
  - Main test: Job spans entire time window and beyond
  - Tests hourly file generation and processing

- **`test_multiple_jobs_with_different_time_spans`**
  - Tests 6 different scenarios (before, within, after, spanning)

- **`test_spot_vs_ondemand_with_time_filtering`**
  - Verifies both spot and on-demand instances work correctly

- **`test_verify_cost_calculation_accuracy`**
  - Ensures costs are calculated only for time within the window

## Next Steps

- Read `README_integration_tests.md` for full documentation
- Look at `test_job_analyzer_integration.py` for test implementation
- Check `test_job_analyzer_time_filtering.py` for faster unit tests
- Review `JobAnalyzer.py` lines 114-156 for the actual filtering logic

## Success Criteria

✓ All 5 integration tests pass
✓ Tests run in < 1 second
✓ No errors or warnings
✓ Time filtering works correctly

You're done! The integration tests verify that JobAnalyzer correctly handles jobs that cross time boundaries.
