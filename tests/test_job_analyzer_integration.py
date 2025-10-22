#!/usr/bin/env python3
'''
Integration tests for JobAnalyzer using the actual class
Tests jobs that start before starttime and end after endtime with real JobAnalyzer

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
'''

import unittest
from unittest.mock import MagicMock, Mock, patch, mock_open
from datetime import datetime, timedelta, timezone
import sys
import os
from tempfile import TemporaryDirectory
import json
import csv

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock missing dependencies before importing
sys.modules['git'] = MagicMock()
sys.modules['colored'] = MagicMock()
sys.modules['boto3'] = MagicMock()
sys.modules['botocore'] = MagicMock()
sys.modules['botocore.exceptions'] = MagicMock()
sys.modules['schema'] = MagicMock()
sys.modules['openpyxl'] = MagicMock()
sys.modules['openpyxl.chart'] = MagicMock()
sys.modules['openpyxl.styles'] = MagicMock()
sys.modules['openpyxl.styles.numbers'] = MagicMock()
sys.modules['openpyxl.utils'] = MagicMock()
sys.modules['openpyxl.utils.units'] = MagicMock()
sys.modules['psutil'] = MagicMock()
sys.modules['packaging'] = MagicMock()
sys.modules['packaging.version'] = MagicMock()
sys.modules['ijson'] = MagicMock()

# Mock yaml with actual functionality
import yaml as real_yaml
sys.modules['yaml'] = real_yaml

from JobAnalyzer import JobAnalyzer, JobCost
from SchedulerJobInfo import SchedulerJobInfo, datetime_to_str, str_to_datetime
from JobAnalyzerBase import SECONDS_PER_HOUR


class TestJobAnalyzerIntegration(unittest.TestCase):
    """Integration tests using the actual JobAnalyzer class"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = TemporaryDirectory()
        self.output_dir = self.temp_dir.name

        # Create a proper config file with all required fields
        self.config_file = os.path.join(self.output_dir, 'test_config.yml')
        config_content = """version: 1

instance_mapping:
  hyperthreading: False
  region_name: us-east-1
  range_minimum: 0
  range_maximum: 1000000
  ram_ranges_GB:
    - 1
    - 2
    - 4
    - 8
    - 16
    - 32
    - 64
    - 128
  runtime_ranges_minutes:
    - 1
    - 5
    - 20
    - 60
    - 240
  instance_prefix_list:
    - c7a
    - m7a

consumption_model_mapping:
  minimum_cpu_speed: 2
  maximum_minutes_for_spot: 60
  ec2_savings_plan_duration: 3
  ec2_savings_plan_payment_option: 'All Upfront'
  compute_savings_plan_duration: 3
  compute_savings_plan_payment_option: 'All Upfront'
  job_file_batch_size: 1000

ComputeClusterModel:
  BootTime: '2:00'
  IdleTime: '4:00'
"""
        with open(self.config_file, 'w') as f:
            f.write(config_content)

        # Create a minimal instance type info JSON file
        self.instance_info_file = os.path.join(self.output_dir, 'instance_type_info.json')
        instance_info = {
            'c7a.large': {
                'DefaultCores': 2,
                'MemoryInGiB': 4,
                'ProcessorInfo': {
                    'SustainedClockSpeedInGhz': 3.0
                },
                'pricing': {
                    'OnDemand': 0.1,
                    'spot': 0.03,
                    'EC2SavingsPlan': {
                        'EC2 SP 3yr All Upfront': 0.06
                    },
                    'ComputeSavingsPlan': {
                        'Compute SP 3yr All Upfront': 0.07
                    }
                }
            },
            'c7a.xlarge': {
                'DefaultCores': 4,
                'MemoryInGiB': 8,
                'ProcessorInfo': {
                    'SustainedClockSpeedInGhz': 3.0
                },
                'pricing': {
                    'OnDemand': 0.2,
                    'spot': 0.06,
                    'EC2SavingsPlan': {
                        'EC2 SP 3yr All Upfront': 0.12
                    },
                    'ComputeSavingsPlan': {
                        'Compute SP 3yr All Upfront': 0.14
                    }
                }
            }
        }

        with open(self.instance_info_file, 'w') as f:
            json.dump(instance_info, f, indent=2)

        # Mock scheduler parser
        self.mock_parser = Mock()

        # Set up test time window
        # Start: 2024-01-01 10:00:00
        # End:   2024-01-01 12:00:00
        self.start_datetime = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        self.end_datetime = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        self.starttime_str = datetime_to_str(self.start_datetime)
        self.endtime_str = datetime_to_str(self.end_datetime)

    def tearDown(self):
        """Clean up test fixtures"""
        self.temp_dir.cleanup()

    def _create_job_analyzer(self):
        """Helper method to create JobAnalyzer with mocked dependencies"""
        # Patch the instance type info file path
        with patch('JobAnalyzerBase.path.join') as mock_join:
            # Make path.join return our test instance_info_file when called for instance_type_info.json
            def side_effect(*args):
                if len(args) >= 2 and args[-1] == 'instance_type_info.json':
                    return self.instance_info_file
                return os.path.join(*args)

            mock_join.side_effect = side_effect

            with patch('JobAnalyzer.EC2InstanceTypeInfo') as mock_ec2_info_class:
                # Mock the EC2InstanceTypeInfo class
                mock_ec2_instance = Mock()
                mock_ec2_info_class.return_value = mock_ec2_instance
                mock_ec2_info_class.get_instance_family.return_value = 'c7a'

                analyzer = JobAnalyzer(
                    scheduler_parser=self.mock_parser,
                    config_filename=self.config_file,
                    output_dir=self.output_dir,
                    starttime=self.starttime_str,
                    endtime=self.endtime_str,
                    queue_filters=None,
                    project_filters=None
                )

                # Manually set instance type info since we're mocking the loading
                with open(self.instance_info_file, 'r') as f:
                    analyzer.instance_type_info = json.load(f)

                analyzer.instance_family_info = {
                    'c7a': {
                        'MaxInstanceType': 'c7a.xlarge',
                        'MaxMemoryInGiB': 8
                    }
                }

                return analyzer

    def test_real_job_analyzer_time_filtering(self):
        """Test that the real JobAnalyzer correctly filters hours before starttime and after endtime"""
        analyzer = self._create_job_analyzer()

        # Test hours: before, within, and after the time range
        before_hour = int(self.start_datetime.timestamp() // SECONDS_PER_HOUR) - 1
        within_hour = int(self.start_datetime.timestamp() // SECONDS_PER_HOUR)
        after_hour = int(self.end_datetime.timestamp() // SECONDS_PER_HOUR) + 1

        # Call _update_hourly_stats for each hour
        for hour in [before_hour, within_hour, after_hour]:
            analyzer._update_hourly_stats(
                round_hour=hour,
                instance_minutes_within_hour=60.0,
                minutes_within_hour=60.0,
                core_hours=2.0,
                total_cost_per_hour=0.1,
                spot=False,
                instance_family='c7a'
            )

        # Verify filtering
        self.assertNotIn(before_hour, analyzer.hourly_stats,
                        "Hour before starttime should be filtered out by real JobAnalyzer")
        self.assertIn(within_hour, analyzer.hourly_stats,
                     "Hour within range should be included by real JobAnalyzer")
        self.assertNotIn(after_hour, analyzer.hourly_stats,
                        "Hour after endtime should be filtered out by real JobAnalyzer")

    def test_job_spanning_time_boundaries_with_hourly_files(self):
        """Test a job that spans before starttime to after endtime with hourly file processing"""
        analyzer = self._create_job_analyzer()

        # Create a job that spans the entire time window and beyond
        job_start = self.start_datetime - timedelta(hours=1)
        job_end = self.end_datetime + timedelta(hours=1)

        job = SchedulerJobInfo(
            job_id=123,
            num_cores=2,
            max_mem_gb=4.0,
            num_hosts=1,
            submit_time=datetime_to_str(job_start - timedelta(minutes=5)),
            start_time=datetime_to_str(job_start),
            finish_time=datetime_to_str(job_end)
        )

        # Create a JobCost object
        job_cost = JobCost(
            job=job,
            spot=False,
            instance_family='c7a',
            instance_type='c7a.large',
            rate=0.1
        )

        # Add job to hourly bucket (this should create hourly files)
        analyzer._add_job_to_hourly_bucket(job_cost)
        analyzer._write_hourly_jobs_buckets_to_file()

        # Get the hourly files that were created
        hourly_files = analyzer.get_hourly_files()

        # Verify that hourly files were created
        self.assertGreater(len(hourly_files), 0, "Hourly files should be created")

        # Process the hourly files with time filtering
        analyzer._process_hourly_jobs()

        # Verify that only hours within the time range were processed
        before_start_hour = int(job_start.timestamp() // SECONDS_PER_HOUR)
        start_hour = int(self.start_datetime.timestamp() // SECONDS_PER_HOUR)
        end_hour = int(self.end_datetime.timestamp() // SECONDS_PER_HOUR)
        after_end_hour = int(job_end.timestamp() // SECONDS_PER_HOUR)

        # Hours before starttime should not be in hourly_stats
        self.assertNotIn(before_start_hour, analyzer.hourly_stats,
                        "Hour before starttime should be filtered during processing")

        # Hours within the range should be in hourly_stats
        hours_in_range = []
        current = start_hour
        while current <= end_hour:
            hours_in_range.append(current)
            current += 1

        for hour in hours_in_range:
            self.assertIn(hour, analyzer.hourly_stats,
                         f"Hour {hour} within time range should be in hourly_stats")

        # Hours after endtime should not be in hourly_stats
        self.assertNotIn(after_end_hour, analyzer.hourly_stats,
                        "Hour after endtime should be filtered during processing")

    def test_multiple_jobs_with_different_time_spans(self):
        """Test multiple jobs with different relationships to the time window"""
        analyzer = self._create_job_analyzer()

        # Job 1: Completely before time window
        job1_start = self.start_datetime - timedelta(hours=3)
        job1_end = self.start_datetime - timedelta(hours=2)

        # Job 2: Starts before, ends within
        job2_start = self.start_datetime - timedelta(minutes=30)
        job2_end = self.start_datetime + timedelta(minutes=30)

        # Job 3: Completely within
        job3_start = self.start_datetime + timedelta(minutes=15)
        job3_end = self.start_datetime + timedelta(minutes=45)

        # Job 4: Starts within, ends after
        job4_start = self.end_datetime - timedelta(minutes=30)
        job4_end = self.end_datetime + timedelta(minutes=30)

        # Job 5: Completely after time window
        job5_start = self.end_datetime + timedelta(hours=2)
        job5_end = self.end_datetime + timedelta(hours=3)

        # Job 6: Spans entire window and beyond
        job6_start = self.start_datetime - timedelta(hours=1)
        job6_end = self.end_datetime + timedelta(hours=1)

        jobs_data = [
            (1, job1_start, job1_end, "before"),
            (2, job2_start, job2_end, "starts_before_ends_within"),
            (3, job3_start, job3_end, "within"),
            (4, job4_start, job4_end, "starts_within_ends_after"),
            (5, job5_start, job5_end, "after"),
            (6, job6_start, job6_end, "spans_all"),
        ]

        for job_id, start, end, label in jobs_data:
            job = SchedulerJobInfo(
                job_id=job_id,
                num_cores=2,
                max_mem_gb=4.0,
                num_hosts=1,
                submit_time=datetime_to_str(start - timedelta(minutes=5)),
                start_time=datetime_to_str(start),
                finish_time=datetime_to_str(end)
            )

            job_cost = JobCost(
                job=job,
                spot=False,
                instance_family='c7a',
                instance_type='c7a.large',
                rate=0.1
            )

            analyzer._add_job_to_hourly_bucket(job_cost)

        # Write and process all jobs
        analyzer._write_hourly_jobs_buckets_to_file()
        analyzer._process_hourly_jobs()

        # Verify only appropriate hours are in hourly_stats
        start_hour = int(self.start_datetime.timestamp() // SECONDS_PER_HOUR)
        end_hour = int(self.end_datetime.timestamp() // SECONDS_PER_HOUR)

        # All hours in hourly_stats should be within the time window
        for hour in analyzer.hourly_stats.keys():
            self.assertGreaterEqual(hour * SECONDS_PER_HOUR, self.start_datetime.timestamp(),
                                  f"Hour {hour} should be >= starttime")
            self.assertLessEqual(hour * SECONDS_PER_HOUR, self.end_datetime.timestamp(),
                               f"Hour {hour} should be <= endtime")

        # Should have data for hours within the window (jobs 2, 3, 4, 6 contribute)
        self.assertGreater(len(analyzer.hourly_stats), 0,
                          "Should have hourly stats for jobs that overlap the time window")

    def test_spot_vs_ondemand_with_time_filtering(self):
        """Test that spot and on-demand jobs are correctly categorized with time filtering"""
        analyzer = self._create_job_analyzer()

        # Short job (eligible for spot) that spans the time window
        short_job_start = self.start_datetime - timedelta(minutes=15)
        short_job_end = self.start_datetime + timedelta(minutes=30)

        short_job = SchedulerJobInfo(
            job_id=1,
            num_cores=2,
            max_mem_gb=4.0,
            num_hosts=1,
            submit_time=datetime_to_str(short_job_start - timedelta(minutes=5)),
            start_time=datetime_to_str(short_job_start),
            finish_time=datetime_to_str(short_job_end)
        )

        # Long job (not eligible for spot) that spans the time window
        long_job_start = self.start_datetime - timedelta(hours=1)
        long_job_end = self.end_datetime + timedelta(hours=1)

        long_job = SchedulerJobInfo(
            job_id=2,
            num_cores=2,
            max_mem_gb=4.0,
            num_hosts=1,
            submit_time=datetime_to_str(long_job_start - timedelta(minutes=5)),
            start_time=datetime_to_str(long_job_start),
            finish_time=datetime_to_str(long_job_end)
        )

        # Add jobs
        short_job_cost = JobCost(short_job, spot=True, instance_family='c7a',
                                instance_type='c7a.large', rate=0.03)
        long_job_cost = JobCost(long_job, spot=False, instance_family='c7a',
                               instance_type='c7a.large', rate=0.1)

        analyzer._add_job_to_hourly_bucket(short_job_cost)
        analyzer._add_job_to_hourly_bucket(long_job_cost)
        analyzer._write_hourly_jobs_buckets_to_file()
        analyzer._process_hourly_jobs()

        # Verify both spot and on-demand stats exist within the time window
        start_hour = int(self.start_datetime.timestamp() // SECONDS_PER_HOUR)

        self.assertIn(start_hour, analyzer.hourly_stats,
                     "Start hour should have stats")

        # Check that we have both spot and on-demand data
        hour_stats = analyzer.hourly_stats[start_hour]
        self.assertIn('spot', hour_stats, "Should have spot stats")
        self.assertIn('on_demand', hour_stats, "Should have on-demand stats")

        # Verify spot and on-demand totals are tracked separately
        self.assertGreaterEqual(hour_stats['spot']['total'], 0,
                              "Should have spot costs")
        self.assertGreaterEqual(hour_stats['on_demand']['total'], 0,
                              "Should have on-demand costs")

    def test_verify_cost_calculation_accuracy(self):
        """Test that costs are calculated correctly for jobs spanning time boundaries"""
        analyzer = self._create_job_analyzer()

        # Job that starts 30 minutes before starttime and runs for 90 minutes
        # Should only count the 60 minutes from starttime to starttime+60min
        job_start = self.start_datetime - timedelta(minutes=30)
        job_end = self.start_datetime + timedelta(minutes=60)

        job = SchedulerJobInfo(
            job_id=1,
            num_cores=2,
            max_mem_gb=4.0,
            num_hosts=1,
            submit_time=datetime_to_str(job_start - timedelta(minutes=5)),
            start_time=datetime_to_str(job_start),
            finish_time=datetime_to_str(job_end)
        )

        hourly_rate = 0.12  # $0.12 per hour
        job_cost = JobCost(job, spot=False, instance_family='c7a',
                          instance_type='c7a.large', rate=hourly_rate)

        analyzer._add_job_to_hourly_bucket(job_cost)
        analyzer._write_hourly_jobs_buckets_to_file()
        analyzer._process_hourly_jobs()

        # Calculate expected cost
        # Job runs 90 minutes total but only 60 minutes are within the time window
        # Expected cost = (60 minutes / 60) * hourly_rate = hourly_rate
        expected_cost = hourly_rate

        # Get the actual cost from hourly_stats
        start_hour = int(self.start_datetime.timestamp() // SECONDS_PER_HOUR)
        actual_cost = analyzer.hourly_stats[start_hour]['on_demand']['total']

        self.assertAlmostEqual(actual_cost, expected_cost, places=4,
                              msg=f"Cost should be calculated only for time within window. "
                                  f"Expected: {expected_cost}, Actual: {actual_cost}")


if __name__ == '__main__':
    unittest.main()
