# JobAnalyzer Integration Tests (Bash Script)

## Overview

This document describes how to run **integration tests** for `JobAnalyzer.py` using the actual class (not mocks) in a proper virtual environment with all dependencies installed.

The tests focus on jobs that **start before the `starttime`** and/or **end after the `endtime`** parameters to verify correct time filtering behavior.

## Files

- **`run_integration_tests.sh`**: Bash script to run integration tests with proper environment setup
- **`test_job_analyzer_integration.py`**: Python integration tests using the real JobAnalyzer class

## Prerequisites

### 1. Source the Setup Script

Before running the integration tests, you **must** source the `setup.sh` script to:
- Create a Python virtual environment (`.venv`)
- Install all required Python packages from `requirements.txt`
- Set up the correct `PYTHONPATH`

```bash
cd /path/to/hpc-cost-simulator
source setup.sh
```

### 2. Verify Environment

The setup script will:
- ✓ Detect your OS (Linux/macOS)
- ✓ Check Python version (>= 3.6 required)
- ✓ Create `.venv` virtual environment
- ✓ Install all dependencies:
  - boto3, botocore (AWS SDK)
  - GitPython
  - openpyxl
  - PyYAML
  - schema
  - colored
  - psutil
  - packaging
  - pytest
  - And more...

## Running the Tests

### Quick Start

```bash
# 1. Navigate to the repository
cd /path/to/hpc-cost-simulator

# 2. Source the setup script (creates venv and installs packages)
source setup.sh

# 3. Run the integration tests
./tests/run_integration_tests.sh
```

### Expected Output

```
========================================
JobAnalyzer Integration Tests
Testing Time Filtering for Jobs
========================================

✓ Virtual environment detected: /path/to/.venv
✓ Using Python 3.x.x
✓ All required packages are installed

========================================
Running Integration Tests
========================================

Test Suite: JobAnalyzer Integration Tests
Testing jobs that span time boundaries:
  - Jobs starting before starttime
  - Jobs ending after endtime
  - Jobs spanning the entire time window

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

Summary:
  - Time filtering logic is working correctly
  - Jobs spanning time boundaries are handled properly
  - Hourly stats are calculated accurately
```

## What Gets Tested

### Integration Test Cases

1. **test_real_job_analyzer_time_filtering**
   - Tests the basic time filtering with real JobAnalyzer instance
   - Verifies hours before/after the time window are excluded
   - Verifies hours within the time window are included

2. **test_job_spanning_time_boundaries_with_hourly_files** ⭐
   - **Main integration test**
   - Creates a job that spans the entire time window and beyond
   - Tests the hourly file generation and processing
   - Verifies that only hours within the time window appear in results

3. **test_multiple_jobs_with_different_time_spans**
   - Tests 6 different job scenarios:
     - Job completely before time window
     - Job starts before, ends within
     - Job completely within
     - Job starts within, ends after
     - Job completely after time window
     - Job spans entire window and beyond
   - Verifies only relevant hours are included

4. **test_spot_vs_ondemand_with_time_filtering**
   - Tests both spot and on-demand instances
   - Verifies they're categorized correctly
   - Ensures time filtering works for both instance types

5. **test_verify_cost_calculation_accuracy**
   - Tests precise cost calculations
   - Job runs 90 minutes but only 60 minutes within window
   - Verifies cost is calculated only for time within the window

## Test Configuration

### Time Window Used
- **Start time**: 2024-01-01 10:00:00 UTC
- **End time**: 2024-01-01 12:00:00 UTC
- **Duration**: 2 hours

### Test Data
- **Instance types**: c7a.large (2 cores, 4GB), c7a.xlarge (4 cores, 8GB)
- **Pricing**: On-demand and spot pricing
- **Job configurations**: Various start/end times relative to the time window

## Differences from Unit Tests

| Aspect | Unit Tests (`test_job_analyzer_time_filtering.py`) | Integration Tests (this) |
|--------|--------------------------------------------------|--------------------------|
| **JobAnalyzer** | Uses MockJobAnalyzer (minimal implementation) | Uses real JobAnalyzer class |
| **Dependencies** | Mocked (git, boto3, openpyxl, etc.) | Real packages required |
| **Environment** | Runs without setup | Requires `source setup.sh` |
| **Speed** | Very fast (~0.002s) | Slower (real file I/O) |
| **Coverage** | Time filtering logic only | End-to-end workflow |
| **Files** | No file I/O | Creates hourly CSV files |
| **Purpose** | Fast unit testing | Realistic integration testing |

## Troubleshooting

### Error: "Python virtual environment is not activated"

**Problem**: You haven't sourced `setup.sh`

**Solution**:
```bash
cd /path/to/hpc-cost-simulator
source setup.sh
./tests/run_integration_tests.sh
```

### Error: "Missing required Python packages"

**Problem**: Dependencies not installed or virtual environment is incomplete

**Solution**:
```bash
# Remove old virtual environment
rm -rf .venv

# Re-run setup
source setup.sh

# Try again
./tests/run_integration_tests.sh
```

### Error: "Cannot find JobAnalyzer.py"

**Problem**: Running from wrong directory

**Solution**:
```bash
# Make sure you're in the hpc-cost-simulator directory
cd /path/to/hpc-cost-simulator
./tests/run_integration_tests.sh
```

### Tests Fail Due to Missing AWS Credentials

**Problem**: Some initialization code may try to access AWS

**Solution**: Set up AWS credentials or ensure mock patches are working properly
```bash
aws configure
# OR
export AWS_ACCESS_KEY_ID=dummy
export AWS_SECRET_ACCESS_KEY=dummy
export AWS_DEFAULT_REGION=us-east-1
```

## Running Tests Manually (Without Bash Script)

If you prefer to run tests manually:

```bash
# 1. Source setup
cd /path/to/hpc-cost-simulator
source setup.sh

# 2. Run specific test
python3 -m unittest tests.test_job_analyzer_integration.TestJobAnalyzerIntegration.test_job_spanning_time_boundaries_with_hourly_files -v

# 3. Run all integration tests
python3 -m unittest tests.test_job_analyzer_integration -v

# 4. Run with pytest (if installed)
pytest tests/test_job_analyzer_integration.py -v
```

## Continuous Integration (CI/CD)

To run these tests in a CI/CD pipeline:

```yaml
# Example GitHub Actions / GitLab CI
steps:
  - name: Setup environment
    run: |
      cd hpc-cost-simulator
      source setup.sh

  - name: Run integration tests
    run: |
      cd hpc-cost-simulator
      ./tests/run_integration_tests.sh
```

## Files Created During Testing

The integration tests create temporary files:
- **Hourly job files**: `output/hourly-files/hourly-*.csv`
- **Config files**: Temporary YAML configuration
- **Instance info**: Temporary JSON with instance type data

These are created in temporary directories and cleaned up automatically.

## Test Data Flow

```
1. Create JobAnalyzer instance
   ↓
2. Configure with starttime/endtime
   ↓
3. Create test jobs (various time spans)
   ↓
4. Add jobs to hourly buckets
   ↓
5. Write jobs to hourly CSV files
   ↓
6. Process hourly files
   ↓
7. Verify time filtering in hourly_stats
   ↓
8. Check that only valid hours are included
```

## Related Documentation

- **`README_time_filtering_tests.md`**: Unit tests with MockJobAnalyzer
- **`test_job_analyzer_time_filtering.py`**: Fast unit tests
- **`test_job_analyzer_integration.py`**: Full integration tests (this document)
- **`../JobAnalyzer.py`**: Main class being tested
- **`../setup.sh`**: Environment setup script

## Support

For issues or questions:
1. Check that `source setup.sh` completed successfully
2. Verify Python version >= 3.6
3. Ensure all dependencies installed: `pip list`
4. Review test output for specific error messages
5. Check temporary directories for debugging files

## Development

To add new integration tests:

1. Edit `test_job_analyzer_integration.py`
2. Add new test method to `TestJobAnalyzerIntegration` class
3. Follow existing patterns for setup/teardown
4. Use real JobAnalyzer instance (not mocks)
5. Test with: `./tests/run_integration_tests.sh`

Example:
```python
def test_my_new_scenario(self):
    """Test description"""
    analyzer = self._create_job_analyzer()

    # Create test jobs
    job = SchedulerJobInfo(...)
    job_cost = JobCost(...)

    # Process
    analyzer._add_job_to_hourly_bucket(job_cost)
    analyzer._write_hourly_jobs_buckets_to_file()
    analyzer._process_hourly_jobs()

    # Verify
    self.assertIn(expected_hour, analyzer.hourly_stats)
```
