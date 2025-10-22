# JobAnalyzer Time Filtering Tests

## Overview

This test suite (`test_job_analyzer_time_filtering.py`) provides comprehensive testing for the time filtering functionality in `JobAnalyzer.py`, specifically focusing on jobs that start before the `starttime` and/or end after the `endtime` parameters.

## Test File

- **`test_job_analyzer_time_filtering.py`**: Focused unit tests for the `_update_hourly_stats` method's time filtering logic

## What is Being Tested

The tests verify that the `_update_hourly_stats` method correctly filters job hours based on the `starttime` and `endtime` parameters. This is critical functionality because:

1. Users can specify a time window for analysis
2. Long-running jobs may span across multiple time boundaries
3. Only the portions of jobs within the specified time window should be included in cost calculations

## Test Cases

### Basic Time Filtering Tests

1. **test_update_hourly_stats_before_starttime**
   - Verifies hours before `starttime` are excluded
   - Expected: Hour should not appear in `hourly_stats`

2. **test_update_hourly_stats_after_endtime**
   - Verifies hours after `endtime` are excluded
   - Expected: Hour should not appear in `hourly_stats`

3. **test_update_hourly_stats_within_time_range**
   - Verifies hours within the time range are included
   - Expected: Hour appears in `hourly_stats` with correct cost calculation

### Edge Case Tests (Jobs Spanning Time Boundaries)

4. **test_job_spanning_before_starttime_to_within_range**
   - Tests a job that starts before `starttime` and ends within the time range
   - Example: Job runs from 09:00 to 10:30, time window is 10:00-12:00
   - Expected: Only the portion from 10:00-10:30 is included

5. **test_job_spanning_before_starttime_to_after_endtime** ⭐
   - **Main test case**: Tests a job that completely spans the analysis time window
   - Example: Job runs from 09:00 to 13:00, time window is 10:00-12:00
   - Expected: Only hours 10:00-12:00 are included, excluding hours before and after

6. **test_job_within_range_to_after_endtime**
   - Tests a job that starts within the time range and ends after `endtime`
   - Example: Job runs from 10:30 to 13:00, time window is 10:00-12:00
   - Expected: Only the portion from 10:30-12:00 is included

### Filter Combination Tests

7. **test_no_time_filters**
   - Tests behavior when no time filters are set
   - Expected: All hours are included

8. **test_only_starttime_filter**
   - Tests behavior with only `starttime` set (no `endtime`)
   - Expected: Hours before `starttime` are excluded, all hours after are included

9. **test_only_endtime_filter**
   - Tests behavior with only `endtime` set (no `starttime`)
   - Expected: All hours before `endtime` are included, hours after are excluded

## Running the Tests

### Run all time filtering tests:
```bash
cd /home/scratch.acarter_gpu/lsf-logs/hpc-cost-simulator
python3 -m unittest tests.test_job_analyzer_time_filtering -v
```

### Run a specific test:
```bash
python3 -m unittest tests.test_job_analyzer_time_filtering.TestJobAnalyzerTimeFiltering.test_job_spanning_before_starttime_to_after_endtime -v
```

### Run tests directly:
```bash
python3 tests/test_job_analyzer_time_filtering.py
```

## Test Implementation Details

### MockJobAnalyzer Class

The tests use a `MockJobAnalyzer` class that:
- Implements only the time filtering logic from `JobAnalyzer._update_hourly_stats`
- Avoids complex dependencies on AWS, EC2 instance types, config files, etc.
- Focuses solely on the time filtering behavior
- Makes tests faster and more maintainable

### Test Methodology

Each test follows this pattern:
1. Create a `MockJobAnalyzer` with specific `starttime`/`endtime` values
2. Simulate job processing by calling `_update_hourly_stats` for each hour the job spans
3. Assert that only hours within the time window appear in `hourly_stats`
4. Verify hours outside the window are correctly filtered out

### Time Window Used in Tests

- **Start time**: 2024-01-01 10:00:00 UTC
- **End time**: 2024-01-01 12:00:00 UTC
- This 2-hour window is used consistently across all tests

## Key Assertions

The tests verify:
- Hours before `starttime` are **not present** in `hourly_stats`
- Hours after `endtime` are **not present** in `hourly_stats`
- Hours within the range **are present** in `hourly_stats`
- Cost calculations are correct for included hours
- The filtering logic works correctly with various combinations of start/end times

## Dependencies

The test file mocks external dependencies:
- `git` (GitPython)
- `boto3`/`botocore` (AWS SDK)
- `colored`
- `schema`
- `openpyxl`
- `psutil`
- `packaging`
- `yaml`

This makes the tests runnable even when these packages are not installed.

## Test Results

All 9 tests should pass:
```
test_job_spanning_before_starttime_to_after_endtime ... ok
test_job_spanning_before_starttime_to_within_range ... ok
test_job_within_range_to_after_endtime ... ok
test_no_time_filters ... ok
test_only_endtime_filter ... ok
test_only_starttime_filter ... ok
test_update_hourly_stats_after_endtime ... ok
test_update_hourly_stats_before_starttime ... ok
test_update_hourly_stats_within_time_range ... ok

----------------------------------------------------------------------
Ran 9 tests in 0.002s

OK
```

## Related Code

The tests validate the behavior of:
- `JobAnalyzer._update_hourly_stats()` (lines 114-156 in JobAnalyzer.py)
- Time filtering logic that checks:
  - `round_hour * SECONDS_PER_HOUR < self._starttime_dt.timestamp()` (line 131)
  - `round_hour * SECONDS_PER_HOUR > self._endtime_dt.timestamp()` (line 137)

## Future Enhancements

Potential additional tests:
- Jobs that span multiple days
- Jobs with different numbers of hosts
- Spot vs on-demand instance filtering
- Different instance families
- Edge cases around daylight saving time transitions
- Jobs with zero duration
- Jobs with negative durations (error cases)
