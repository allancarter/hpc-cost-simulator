# JobAnalyzer CSV End-to-End Tests

## Overview

This test suite provides **complete end-to-end validation** of the JobAnalyzer workflow using synthetic CSV input files. Unlike other tests, these tests:

1. ✅ Create a synthetic `jobs.csv` file with test data
2. ✅ Run the **actual `JobAnalyzer.py`** (not mocked)
3. ✅ Parse jobs using **`CSVLogParser`** (real parser)
4. ✅ Validate the **`hourly_stats.csv` output file**
5. ✅ Verify time filtering for jobs spanning time boundaries

## Files

- **`test_job_analyzer_csv_e2e.py`**: Python end-to-end tests using CSV workflow
- **`run_csv_e2e_tests.sh`**: Bash script to run the E2E tests

## Test Workflow

```
┌─────────────────────────────────────────────────────────┐
│  1. Create Synthetic jobs.csv                          │
│     - Define test jobs with specific start/end times   │
│     - Jobs before, within, after, and spanning window  │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  2. Run CSVLogParser                                    │
│     - Parse jobs.csv file                              │
│     - Apply starttime/endtime filters                  │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  3. Run JobAnalyzer                                     │
│     - Process each job                                  │
│     - Map to instance types                            │
│     - Create hourly CSV files                          │
│     - Process hourly files                             │
│     - Generate hourly_stats.csv                        │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  4. Validate Output                                     │
│     - Read hourly_stats.csv                            │
│     - Verify only correct hours are included           │
│     - Check cost calculations                          │
│     - Validate instance hours                          │
└─────────────────────────────────────────────────────────┘
```

## Prerequisites

### 1. Source Setup Script

```bash
cd /path/to/hpc-cost-simulator
source setup.sh
```

This creates the virtual environment and installs all dependencies.

### 2. Verify Environment

The setup script installs:
- boto3, botocore
- GitPython
- openpyxl
- PyYAML
- schema, colored, psutil, packaging
- And more...

## Running the Tests

### Quick Start

```bash
# 1. Navigate to repository
cd /home/scratch.acarter_gpu/lsf-logs/hpc-cost-simulator

# 2. Source setup script
source setup.sh

# 3. Run CSV E2E tests
./tests/run_csv_e2e_tests.sh
```

### Expected Output

```
========================================
JobAnalyzer CSV End-to-End Tests
Complete Workflow Validation
========================================

✓ Virtual environment detected: /path/to/.venv
✓ Using Python 3.x.x
✓ All required packages are installed

========================================
Running CSV End-to-End Tests
========================================

Test Workflow:
  1. Create synthetic jobs.csv with test data
  2. Run actual JobAnalyzer.py to process CSV
  3. Validate hourly_stats.csv output file
  4. Verify time filtering is correct

Test Scenarios:
  • Job spanning entire time window and beyond
  • Job starting before, ending within window
  • Job starting within, ending after window
  • Multiple jobs with different time relationships
  • Spot eligible vs long-running jobs
  • Cost calculation accuracy for partial hours
  • Jobs completely outside time window

test_cost_calculation_accuracy_for_partial_hours ... ok
test_job_spanning_entire_time_window ... ok
test_job_starting_before_ending_within_window ... ok
test_job_starting_within_ending_after_window ... ok
test_multiple_jobs_with_different_time_relationships ... ok
test_no_jobs_within_time_window ... ok
test_spot_eligible_vs_long_running_jobs ... ok
test_summary_stats_csv_created ... ok

----------------------------------------------------------------------
Ran 8 tests in X.XXXs

OK

========================================
✓ All CSV E2E Tests Passed!
========================================

Summary:
  ✓ Synthetic CSV files created successfully
  ✓ JobAnalyzer processed jobs correctly
  ✓ hourly_stats.csv output validated
  ✓ Time filtering working as expected
  ✓ Cost calculations accurate
```

## Test Cases

### 1. test_job_spanning_entire_time_window ⭐

**Main test case**: Job that completely spans the time window and beyond.

**Scenario:**
```
Timeline:
09:00 -------- 10:00 -------- 11:00 -------- 12:00 -------- 13:00 -------- 14:00 -------- 15:00
      job_start       starttime                                          endtime       job_end
|--------------------------------- Job Duration (6 hours) ---------------------------------|
                     |---------------------- Window (4 hours) ----------------------|
```

**Expected:** Only hours 10:00-14:00 appear in `hourly_stats.csv` (4 hours total)

**Validates:**
- Hours before starttime excluded
- Hours after endtime excluded
- Correct number of hours in output
- Instance hours calculated correctly

### 2. test_multiple_jobs_with_different_time_relationships

Tests 6 different job scenarios:

| Job | Start | End | Relationship | Expected |
|-----|-------|-----|--------------|----------|
| 1 | 08:00 | 09:00 | Before window | Excluded |
| 2 | 09:30 | 11:00 | Starts before, ends within | Partial (10:00-11:00) |
| 3 | 11:00 | 13:00 | Completely within | Fully counted |
| 4 | 13:30 | 15:00 | Starts within, ends after | Partial (13:30-14:00) |
| 5 | 15:00 | 16:00 | After window | Excluded |
| 6 | 09:00 | 15:00 | Spans entire window | Fully counted (10:00-14:00) |

**Validates:**
- Multiple jobs processed correctly
- Each relationship to time window handled properly
- No interference between jobs

### 3. test_job_starting_before_ending_within_window

**Scenario:**
```
08:00 -------- 10:00 -------- 11:00 -------- 14:00
      job_start       starttime   job_end   endtime
|------- Job (3h) -------|
                |--- Window (4h) ---|
```

**Expected:** Only 1 hour (10:00-11:00) counted

**Validates:**
- Job starting before starttime correctly trimmed
- Only portion within window counted
- Accurate instance hours (~1.0)

### 4. test_job_starting_within_ending_after_window

**Scenario:**
```
10:00 -------- 13:00 -------- 14:00 -------- 15:00
starttime    job_start   endtime       job_end
             |------- Job (2h) -------|
|--- Window (4h) ---|
```

**Expected:** Only 1 hour (13:00-14:00) counted

**Validates:**
- Job ending after endtime correctly trimmed
- Only portion within window counted

### 5. test_spot_eligible_vs_long_running_jobs

Tests both spot and on-demand instances:

| Job | Duration | Spot Eligible | Expected Category |
|-----|----------|---------------|-------------------|
| 1 | 30 min | Yes | Spot |
| 2 | 8 hours | No | On-Demand |

**Validates:**
- Spot eligibility threshold works
- Both categories processed correctly
- Costs calculated for appropriate category

### 6. test_cost_calculation_accuracy_for_partial_hours

**Scenario:**
```
09:30 -------- 10:00 -------- 10:30
      job_start       starttime   job_end

Job runs: 1 hour total (09:30-10:30)
Window overlaps: 30 minutes (10:00-10:30)
```

**Expected:**
- Instance hours = 0.5 (30 minutes)
- Cost = (30/60) * hourly_rate

**Validates:**
- Precise fractional hour calculations
- Costs accurately prorated for partial hours

### 7. test_no_jobs_within_time_window

Tests edge case where all jobs are outside the window.

**Expected:**
- `hourly_stats.csv` created with zero activity
- Total instance hours = 0

**Validates:**
- No false positives
- Empty windows handled correctly

### 8. test_summary_stats_csv_created

**Validates:**
- `summary_stats.csv` is created
- Contains expected data structure
- Summary statistics are accurate

## Synthetic CSV Format

The tests create CSV files matching the SchedulerJobInfo format:

```csv
job_id,num_cores,max_mem_gb,num_hosts,submit_time,start_time,finish_time,wait_time,run_time,queue,project
1,2,4.0,1,2024-01-15T09:55:00+00:00,2024-01-15T10:00:00+00:00,2024-01-15T14:00:00+00:00,00:05:00,04:00:00,normal,test_project
```

### Fields Explained

- **job_id**: Unique identifier
- **num_cores**: Number of CPU cores
- **max_mem_gb**: Maximum memory in GB
- **num_hosts**: Number of hosts/instances
- **submit_time**: When job was submitted
- **start_time**: When job started
- **finish_time**: When job finished
- **wait_time**: Time between submit and start (MM:SS format)
- **run_time**: Total runtime (HH:MM:SS format)
- **queue**: Queue name
- **project**: Project name

## Output Validation

### hourly_stats.csv Structure

```csv
Relative Hour,Total OnDemand Costs,Total Spot Costs,Instance Hours,c7a,m7a,...
0,0.1020,0.0,1.0,0.1020,0.0,...
1,0.1020,0.0,1.0,0.1020,0.0,...
2,0.1020,0.0,1.0,0.1020,0.0,...
3,0.1020,0.0,1.0,0.1020,0.0,...
```

### What Gets Validated

✅ **Relative Hour**: Sequential hours (0, 1, 2, 3, ...)
✅ **Total OnDemand Costs**: Sum of all on-demand costs for that hour
✅ **Total Spot Costs**: Sum of all spot costs for that hour
✅ **Instance Hours**: Total instance hours for that hour
✅ **Instance Family Columns**: Costs broken down by family

### Assertions Made

```python
# Correct number of hours
assert len(hourly_stats) == expected_hours

# Each hour has data
assert hourly_stats[hour]['Instance Hours'] > 0

# Total matches expected
total_hours = sum(h['Instance Hours'] for h in hourly_stats.values())
assert total_hours ≈ expected_total

# Costs are reasonable
assert total_costs > 0
```

## Test Time Window

All tests use a consistent time window:
- **Start time**: 2024-01-15 10:00:00 UTC
- **End time**: 2024-01-15 14:00:00 UTC
- **Duration**: 4 hours

This provides a clear, manageable window for testing.

## Instance Types Used

```json
{
  "c7a.large": {
    "DefaultCores": 2,
    "MemoryInGiB": 4,
    "pricing": {
      "OnDemand": 0.1020,
      "spot": 0.0306
    }
  },
  "c7a.xlarge": {
    "DefaultCores": 4,
    "MemoryInGiB": 8,
    "pricing": {
      "OnDemand": 0.2040,
      "spot": 0.0612
    }
  },
  "m7a.large": {
    "DefaultCores": 2,
    "MemoryInGiB": 8,
    "pricing": {
      "OnDemand": 0.1088,
      "spot": 0.0326
    }
  }
}
```

## Comparison with Other Tests

| Aspect | Unit Tests | Integration Tests | **CSV E2E Tests** |
|--------|-----------|-------------------|-------------------|
| JobAnalyzer | MockJobAnalyzer | Real | **Real** |
| Input | Direct function calls | Direct function calls | **Synthetic CSV file** |
| Parser | None | Mocked | **Real CSVLogParser** |
| Output | In-memory only | In-memory + temp files | **Real CSV files** |
| Validation | Assert on memory | Assert on memory | **Read and validate CSV** |
| Workflow | Partial | Nearly complete | **Complete E2E** |
| Realism | Low | Medium | **High** |

**CSV E2E tests are the most realistic** - they test the actual workflow a user would follow.

## Running Tests Manually

```bash
# After sourcing setup.sh

# Run all CSV E2E tests
python3 -m unittest tests.test_job_analyzer_csv_e2e -v

# Run specific test
python3 -m unittest tests.test_job_analyzer_csv_e2e.TestJobAnalyzerCSVEndToEnd.test_job_spanning_entire_time_window -v

# Run with pytest (if installed)
pytest tests/test_job_analyzer_csv_e2e.py -v
```

## Debugging

### View Generated CSV Files

Tests create temporary files. To debug, modify test to keep temp directory:

```python
def setUp(self):
    self.temp_dir = TemporaryDirectory(delete=False)  # Don't auto-delete
    print(f"Temp dir: {self.temp_dir.name}")
```

Then inspect:
```bash
cat /tmp/tmp*/jobs.csv
cat /tmp/tmp*/output/hourly_stats.csv
cat /tmp/tmp*/output/summary_stats.csv
```

### Common Issues

1. **"No hourly_stats.csv created"**
   - Check that jobs overlap the time window
   - Verify time zone handling (all times use UTC)

2. **"Instance hours don't match expected"**
   - Check job start/end times are correct
   - Verify calculation: (minutes_in_window / 60) * num_hosts

3. **"Costs are zero"**
   - Verify instance type info is loaded
   - Check pricing data in mock

## Development

### Adding New Test Cases

```python
def test_my_new_scenario(self):
    """Test description"""
    # Define job times
    job_start = self.start_datetime - timedelta(hours=1)
    job_end = self.end_datetime + timedelta(hours=1)

    # Create jobs data
    jobs_data = [
        (1, job_start, job_end, 2, 4.0, 1)
    ]

    # Run workflow
    csv_file = self._create_synthetic_jobs_csv(jobs_data)
    analyzer = self._run_job_analyzer(csv_file)

    # Validate output
    hourly_stats = self._read_hourly_stats_csv()

    # Assertions
    self.assertIn(0, hourly_stats)
    # ... more assertions
```

### Testing Different Instance Types

Modify `instance_info_file` in `setUp()` to add new types:

```python
instance_info['r7a.large'] = {
    'DefaultCores': 2,
    'MemoryInGiB': 16,
    # ...
}
```

## CI/CD Integration

```yaml
# .github/workflows/test.yml
name: CSV E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Setup Environment
        run: |
          cd hpc-cost-simulator
          source setup.sh

      - name: Run CSV E2E Tests
        run: |
          cd hpc-cost-simulator
          ./tests/run_csv_e2e_tests.sh
```

## Success Criteria

✅ All 8 tests pass
✅ CSV files created and parsed correctly
✅ hourly_stats.csv contains expected data
✅ Time filtering works correctly
✅ Costs calculated accurately
✅ No errors or warnings

## Support

For issues:
1. Check bash script output for specific errors
2. Verify `source setup.sh` completed
3. Ensure all dependencies installed
4. Check temp directories for generated files
5. Review test output for assertion failures

## Related Documentation

- **`QUICKSTART.md`**: Quick start guide
- **`README_integration_tests.md`**: Integration tests with real JobAnalyzer
- **`README_time_filtering_tests.md`**: Unit tests with MockJobAnalyzer
- **`TEST_SUMMARY.md`**: Complete test suite overview

## Conclusion

These CSV end-to-end tests provide the **most realistic validation** of the JobAnalyzer workflow. They:

✅ Use actual JobAnalyzer.py (no mocks)
✅ Process real CSV files (like production)
✅ Validate actual output files
✅ Test complete workflow from input to output
✅ Verify time filtering for boundary-spanning jobs

**Total Tests**: 8 comprehensive end-to-end scenarios
**Coverage**: Complete CSV → JobAnalyzer → CSV output workflow
**Realism**: Highest - matches actual user workflow

Perfect for release validation and regression testing! 🎉
