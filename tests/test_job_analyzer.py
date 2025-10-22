#!/usr/bin/env python3
'''
Tests for JobAnalyzer.py focusing on jobs that start before starttime and end after endtime

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
sys.modules['yaml'] = MagicMock()

from JobAnalyzer import JobAnalyzer, JobCost
from SchedulerJobInfo import SchedulerJobInfo, datetime_to_str, str_to_datetime
from JobAnalyzerBase import SECONDS_PER_HOUR


class TestJobAnalyzerTimeFiltering(unittest.TestCase):
    """Test cases for JobAnalyzer with time filtering, focusing on edge cases
    where jobs start before starttime and/or end after endtime"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = TemporaryDirectory()
        self.output_dir = self.temp_dir.name
        
        # Create a minimal config file
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
        self.instance_info = {
            'c7a.large': {
                'DefaultCores': 2,
                'MemoryInGiB': 4,
                'pricing': {
                    'OnDemand': 0.1,
                    'spot': 0.03,
                    'EC2SavingsPlan': {'EC2 SP 3yr All Upfront': 0.06},
                    'ComputeSavingsPlan': {'Compute SP 3yr All Upfront': 0.07}
                }
            }
        }
        
        # Mock scheduler parser
        self.mock_parser = Mock()
        
        # Set up test time window
        # Using specific dates for testing
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
        with patch('JobAnalyzer.EC2InstanceTypeInfo') as mock_ec2_info:
            # Mock EC2 instance type info
            mock_ec2_info.get_instance_family.return_value = 'c7a'
            
            analyzer = JobAnalyzer(
                scheduler_parser=self.mock_parser,
                config_filename=self.config_file,
                output_dir=self.output_dir,
                starttime=self.starttime_str,
                endtime=self.endtime_str,
                queue_filters=None,
                project_filters=None
            )
            
            # Mock instance type info
            analyzer.instance_type_info = self.instance_info
            analyzer.instance_family_info = {
                'c7a': {
                    'MaxInstanceType': 'c7a.large'
                }
            }
            
            return analyzer

    def test_update_hourly_stats_round_hour_before_starttime(self):
        """Test that _update_hourly_stats skips hours before starttime"""
        analyzer = self._create_job_analyzer()
        
        # Get the hour before starttime
        before_starttime_hour = int(self.start_datetime.timestamp() // SECONDS_PER_HOUR) - 1
        
        # Call _update_hourly_stats with an hour before starttime
        analyzer._update_hourly_stats(
            round_hour=before_starttime_hour,
            instance_minutes_within_hour=60.0,
            minutes_within_hour=60.0,
            core_hours=2.0,
            total_cost_per_hour=0.1,
            spot=False,
            instance_family='c7a'
        )
        
        # Verify that the hour was NOT added to hourly_stats
        self.assertNotIn(before_starttime_hour, analyzer.hourly_stats,
                        "Hour before starttime should not be added to hourly_stats")

    def test_update_hourly_stats_round_hour_after_endtime(self):
        """Test that _update_hourly_stats skips hours after endtime"""
        analyzer = self._create_job_analyzer()
        
        # Get the hour after endtime
        after_endtime_hour = int(self.end_datetime.timestamp() // SECONDS_PER_HOUR) + 1
        
        # Call _update_hourly_stats with an hour after endtime
        analyzer._update_hourly_stats(
            round_hour=after_endtime_hour,
            instance_minutes_within_hour=60.0,
            minutes_within_hour=60.0,
            core_hours=2.0,
            total_cost_per_hour=0.1,
            spot=False,
            instance_family='c7a'
        )
        
        # Verify that the hour was NOT added to hourly_stats
        self.assertNotIn(after_endtime_hour, analyzer.hourly_stats,
                        "Hour after endtime should not be added to hourly_stats")

    def test_update_hourly_stats_within_time_range(self):
        """Test that _update_hourly_stats includes hours within the time range"""
        analyzer = self._create_job_analyzer()
        
        # Get an hour within the time range
        within_range_hour = int(self.start_datetime.timestamp() // SECONDS_PER_HOUR)
        
        # Call _update_hourly_stats with an hour within range
        analyzer._update_hourly_stats(
            round_hour=within_range_hour,
            instance_minutes_within_hour=60.0,
            minutes_within_hour=60.0,
            core_hours=2.0,
            total_cost_per_hour=0.1,
            spot=False,
            instance_family='c7a'
        )
        
        # Verify that the hour WAS added to hourly_stats
        self.assertIn(within_range_hour, analyzer.hourly_stats,
                     "Hour within time range should be added to hourly_stats")
        
        # Verify the cost was properly calculated
        expected_cost = 60.0 / 60 * 0.1  # (minutes_within_hour / 60) * total_cost_per_hour
        self.assertAlmostEqual(
            analyzer.hourly_stats[within_range_hour]['on_demand']['total'],
            expected_cost,
            places=6,
            msg="Cost should be calculated correctly"
        )

    def test_job_spanning_before_starttime_to_within_range(self):
        """Test a job that starts before starttime and ends within the time range"""
        analyzer = self._create_job_analyzer()
        
        # Job starts 1 hour before starttime and ends 30 minutes after starttime
        job_start = self.start_datetime - timedelta(hours=1)
        job_end = self.start_datetime + timedelta(minutes=30)
        
        # Create a test job
        job = SchedulerJobInfo(
            job_id=1,
            num_cores=2,
            max_mem_gb=4.0,
            num_hosts=1,
            submit_time=datetime_to_str(job_start - timedelta(minutes=5)),
            start_time=datetime_to_str(job_start),
            finish_time=datetime_to_str(job_end)
        )
        
        # Process the job through the hourly bucketing
        job_cost_data = JobCost(
            job=job,
            spot=False,
            instance_family='c7a',
            instance_type='c7a.large',
            rate=0.1
        )
        
        # Simulate what _process_hourly_jobs does
        start_time = job_start.timestamp()
        end_time = job_end.timestamp()
        round_hour = int(start_time // SECONDS_PER_HOUR)
        total_hourly_rate = 0.1 * job.num_hosts
        num_cores = 2
        
        # Process each hour the job spans
        round_hour_seconds = round_hour * SECONDS_PER_HOUR
        processed_hours = []
        
        while round_hour_seconds < end_time:
            next_round_hour = round_hour + 1
            next_round_hour_seconds = next_round_hour * SECONDS_PER_HOUR
            
            if round_hour_seconds <= start_time < next_round_hour_seconds:
                # Job started in this hour
                if end_time <= next_round_hour_seconds:
                    # Job ended within hour
                    runtime_minutes = (end_time - start_time) / 60
                else:
                    # Job spills into the next hour
                    runtime_minutes = (next_round_hour_seconds - start_time) / 60
            elif start_time <= round_hour_seconds and end_time > next_round_hour_seconds:
                # Job started before this hour and runs throughout the hour
                runtime_minutes = 60
            elif start_time < round_hour_seconds and end_time <= next_round_hour_seconds:
                # Job started in prev hour, ends in this one
                runtime_minutes = (end_time - round_hour_seconds) / 60
            else:
                runtime_minutes = 0
                
            instance_minutes = runtime_minutes * job.num_hosts
            core_hours = runtime_minutes * job.num_hosts * num_cores / 60
            
            # Track which hours we processed
            processed_hours.append((round_hour, runtime_minutes))
            
            analyzer._update_hourly_stats(
                round_hour=round_hour,
                instance_minutes_within_hour=instance_minutes,
                minutes_within_hour=runtime_minutes,
                core_hours=core_hours,
                total_cost_per_hour=total_hourly_rate,
                spot=False,
                instance_family='c7a'
            )
            
            round_hour += 1
            round_hour_seconds = round_hour * SECONDS_PER_HOUR
        
        # The hour before starttime should not be in hourly_stats
        before_start_hour = int(job_start.timestamp() // SECONDS_PER_HOUR)
        self.assertNotIn(before_start_hour, analyzer.hourly_stats,
                        "Hour before starttime should be filtered out")
        
        # The hour at starttime should be in hourly_stats
        start_hour = int(self.start_datetime.timestamp() // SECONDS_PER_HOUR)
        self.assertIn(start_hour, analyzer.hourly_stats,
                     "Hour at starttime should be included")

    def test_job_spanning_before_starttime_to_after_endtime(self):
        """Test a job that starts before starttime and ends after endtime"""
        analyzer = self._create_job_analyzer()
        
        # Job starts 1 hour before starttime and ends 1 hour after endtime
        job_start = self.start_datetime - timedelta(hours=1)
        job_end = self.end_datetime + timedelta(hours=1)
        
        # Create a test job
        job = SchedulerJobInfo(
            job_id=2,
            num_cores=4,
            max_mem_gb=8.0,
            num_hosts=1,
            submit_time=datetime_to_str(job_start - timedelta(minutes=5)),
            start_time=datetime_to_str(job_start),
            finish_time=datetime_to_str(job_end)
        )
        
        # Process the job through the hourly bucketing
        job_cost_data = JobCost(
            job=job,
            spot=False,
            instance_family='c7a',
            instance_type='c7a.large',
            rate=0.1
        )
        
        # Simulate what _process_hourly_jobs does
        start_time = job_start.timestamp()
        end_time = job_end.timestamp()
        round_hour = int(start_time // SECONDS_PER_HOUR)
        total_hourly_rate = 0.1 * job.num_hosts
        num_cores = 4
        
        # Process each hour the job spans
        round_hour_seconds = round_hour * SECONDS_PER_HOUR
        
        while round_hour_seconds < end_time:
            next_round_hour = round_hour + 1
            next_round_hour_seconds = next_round_hour * SECONDS_PER_HOUR
            
            if round_hour_seconds <= start_time < next_round_hour_seconds:
                # Job started in this hour
                if end_time <= next_round_hour_seconds:
                    runtime_minutes = (end_time - start_time) / 60
                else:
                    runtime_minutes = (next_round_hour_seconds - start_time) / 60
            elif start_time <= round_hour_seconds and end_time > next_round_hour_seconds:
                # Job started before this hour and runs throughout the hour
                runtime_minutes = 60
            elif start_time < round_hour_seconds and end_time <= next_round_hour_seconds:
                # Job started in prev hour, ends in this one
                runtime_minutes = (end_time - round_hour_seconds) / 60
            else:
                runtime_minutes = 0
                
            instance_minutes = runtime_minutes * job.num_hosts
            core_hours = runtime_minutes * job.num_hosts * num_cores / 60
            
            analyzer._update_hourly_stats(
                round_hour=round_hour,
                instance_minutes_within_hour=instance_minutes,
                minutes_within_hour=runtime_minutes,
                core_hours=core_hours,
                total_cost_per_hour=total_hourly_rate,
                spot=False,
                instance_family='c7a'
            )
            
            round_hour += 1
            round_hour_seconds = round_hour * SECONDS_PER_HOUR
        
        # The hour before starttime should not be in hourly_stats
        before_start_hour = int(job_start.timestamp() // SECONDS_PER_HOUR)
        self.assertNotIn(before_start_hour, analyzer.hourly_stats,
                        "Hour before starttime should be filtered out")
        
        # Hours within the time range should be in hourly_stats
        start_hour = int(self.start_datetime.timestamp() // SECONDS_PER_HOUR)
        self.assertIn(start_hour, analyzer.hourly_stats,
                     "Hours within time range should be included")
        
        # The hour after endtime should not be in hourly_stats
        after_end_hour = int(self.end_datetime.timestamp() // SECONDS_PER_HOUR) + 1
        self.assertNotIn(after_end_hour, analyzer.hourly_stats,
                        "Hour after endtime should be filtered out")

    def test_job_within_time_range_to_after_endtime(self):
        """Test a job that starts within the time range and ends after endtime"""
        analyzer = self._create_job_analyzer()
        
        # Job starts 30 minutes after starttime and ends 1 hour after endtime
        job_start = self.start_datetime + timedelta(minutes=30)
        job_end = self.end_datetime + timedelta(hours=1)
        
        # Create a test job
        job = SchedulerJobInfo(
            job_id=3,
            num_cores=2,
            max_mem_gb=4.0,
            num_hosts=1,
            submit_time=datetime_to_str(job_start - timedelta(minutes=5)),
            start_time=datetime_to_str(job_start),
            finish_time=datetime_to_str(job_end)
        )
        
        # Process the job through the hourly bucketing
        job_cost_data = JobCost(
            job=job,
            spot=False,
            instance_family='c7a',
            instance_type='c7a.large',
            rate=0.1
        )
        
        # Simulate what _process_hourly_jobs does
        start_time = job_start.timestamp()
        end_time = job_end.timestamp()
        round_hour = int(start_time // SECONDS_PER_HOUR)
        total_hourly_rate = 0.1 * job.num_hosts
        num_cores = 2
        
        # Process each hour the job spans
        round_hour_seconds = round_hour * SECONDS_PER_HOUR
        
        while round_hour_seconds < end_time:
            next_round_hour = round_hour + 1
            next_round_hour_seconds = next_round_hour * SECONDS_PER_HOUR
            
            if round_hour_seconds <= start_time < next_round_hour_seconds:
                # Job started in this hour
                if end_time <= next_round_hour_seconds:
                    runtime_minutes = (end_time - start_time) / 60
                else:
                    runtime_minutes = (next_round_hour_seconds - start_time) / 60
            elif start_time <= round_hour_seconds and end_time > next_round_hour_seconds:
                # Job started before this hour and runs throughout the hour
                runtime_minutes = 60
            elif start_time < round_hour_seconds and end_time <= next_round_hour_seconds:
                # Job started in prev hour, ends in this one
                runtime_minutes = (end_time - round_hour_seconds) / 60
            else:
                runtime_minutes = 0
                
            instance_minutes = runtime_minutes * job.num_hosts
            core_hours = runtime_minutes * job.num_hosts * num_cores / 60
            
            analyzer._update_hourly_stats(
                round_hour=round_hour,
                instance_minutes_within_hour=instance_minutes,
                minutes_within_hour=runtime_minutes,
                core_hours=core_hours,
                total_cost_per_hour=total_hourly_rate,
                spot=False,
                instance_family='c7a'
            )
            
            round_hour += 1
            round_hour_seconds = round_hour * SECONDS_PER_HOUR
        
        # Hours within the time range should be in hourly_stats
        start_hour = int(job_start.timestamp() // SECONDS_PER_HOUR)
        self.assertIn(start_hour, analyzer.hourly_stats,
                     "Hour where job started (within range) should be included")
        
        # The hour after endtime should not be in hourly_stats
        after_end_hour = int(self.end_datetime.timestamp() // SECONDS_PER_HOUR) + 1
        self.assertNotIn(after_end_hour, analyzer.hourly_stats,
                        "Hour after endtime should be filtered out")

    def test_job_completely_before_starttime(self):
        """Test a job that starts and ends completely before starttime"""
        analyzer = self._create_job_analyzer()
        
        # Job starts 2 hours before starttime and ends 1 hour before starttime
        job_start = self.start_datetime - timedelta(hours=2)
        job_end = self.start_datetime - timedelta(hours=1)
        
        # Create a test job
        job = SchedulerJobInfo(
            job_id=4,
            num_cores=2,
            max_mem_gb=4.0,
            num_hosts=1,
            submit_time=datetime_to_str(job_start - timedelta(minutes=5)),
            start_time=datetime_to_str(job_start),
            finish_time=datetime_to_str(job_end)
        )
        
        # Process the job through the hourly bucketing
        start_time = job_start.timestamp()
        end_time = job_end.timestamp()
        round_hour = int(start_time // SECONDS_PER_HOUR)
        total_hourly_rate = 0.1 * job.num_hosts
        num_cores = 2
        
        # Process each hour the job spans
        round_hour_seconds = round_hour * SECONDS_PER_HOUR
        
        while round_hour_seconds < end_time:
            next_round_hour = round_hour + 1
            next_round_hour_seconds = next_round_hour * SECONDS_PER_HOUR
            
            if round_hour_seconds <= start_time < next_round_hour_seconds:
                if end_time <= next_round_hour_seconds:
                    runtime_minutes = (end_time - start_time) / 60
                else:
                    runtime_minutes = (next_round_hour_seconds - start_time) / 60
            elif start_time <= round_hour_seconds and end_time > next_round_hour_seconds:
                runtime_minutes = 60
            elif start_time < round_hour_seconds and end_time <= next_round_hour_seconds:
                runtime_minutes = (end_time - round_hour_seconds) / 60
            else:
                runtime_minutes = 0
                
            instance_minutes = runtime_minutes * job.num_hosts
            core_hours = runtime_minutes * job.num_hosts * num_cores / 60
            
            analyzer._update_hourly_stats(
                round_hour=round_hour,
                instance_minutes_within_hour=instance_minutes,
                minutes_within_hour=runtime_minutes,
                core_hours=core_hours,
                total_cost_per_hour=total_hourly_rate,
                spot=False,
                instance_family='c7a'
            )
            
            round_hour += 1
            round_hour_seconds = round_hour * SECONDS_PER_HOUR
        
        # All hours should be filtered out (no hours should be in hourly_stats)
        self.assertEqual(len(analyzer.hourly_stats), 0,
                        "Job completely before starttime should have all hours filtered out")

    def test_job_completely_after_endtime(self):
        """Test a job that starts and ends completely after endtime"""
        analyzer = self._create_job_analyzer()
        
        # Job starts 1 hour after endtime and ends 2 hours after endtime
        job_start = self.end_datetime + timedelta(hours=1)
        job_end = self.end_datetime + timedelta(hours=2)
        
        # Create a test job
        job = SchedulerJobInfo(
            job_id=5,
            num_cores=2,
            max_mem_gb=4.0,
            num_hosts=1,
            submit_time=datetime_to_str(job_start - timedelta(minutes=5)),
            start_time=datetime_to_str(job_start),
            finish_time=datetime_to_str(job_end)
        )
        
        # Process the job through the hourly bucketing
        start_time = job_start.timestamp()
        end_time = job_end.timestamp()
        round_hour = int(start_time // SECONDS_PER_HOUR)
        total_hourly_rate = 0.1 * job.num_hosts
        num_cores = 2
        
        # Process each hour the job spans
        round_hour_seconds = round_hour * SECONDS_PER_HOUR
        
        while round_hour_seconds < end_time:
            next_round_hour = round_hour + 1
            next_round_hour_seconds = next_round_hour * SECONDS_PER_HOUR
            
            if round_hour_seconds <= start_time < next_round_hour_seconds:
                if end_time <= next_round_hour_seconds:
                    runtime_minutes = (end_time - start_time) / 60
                else:
                    runtime_minutes = (next_round_hour_seconds - start_time) / 60
            elif start_time <= round_hour_seconds and end_time > next_round_hour_seconds:
                runtime_minutes = 60
            elif start_time < round_hour_seconds and end_time <= next_round_hour_seconds:
                runtime_minutes = (end_time - round_hour_seconds) / 60
            else:
                runtime_minutes = 0
                
            instance_minutes = runtime_minutes * job.num_hosts
            core_hours = runtime_minutes * job.num_hosts * num_cores / 60
            
            analyzer._update_hourly_stats(
                round_hour=round_hour,
                instance_minutes_within_hour=instance_minutes,
                minutes_within_hour=runtime_minutes,
                core_hours=core_hours,
                total_cost_per_hour=total_hourly_rate,
                spot=False,
                instance_family='c7a'
            )
            
            round_hour += 1
            round_hour_seconds = round_hour * SECONDS_PER_HOUR
        
        # All hours should be filtered out (no hours should be in hourly_stats)
        self.assertEqual(len(analyzer.hourly_stats), 0,
                        "Job completely after endtime should have all hours filtered out")

    def test_job_within_time_range(self):
        """Test a job that starts and ends completely within the time range"""
        analyzer = self._create_job_analyzer()
        
        # Job starts 30 minutes after starttime and ends 30 minutes before endtime
        job_start = self.start_datetime + timedelta(minutes=30)
        job_end = self.end_datetime - timedelta(minutes=30)
        
        # Create a test job
        job = SchedulerJobInfo(
            job_id=6,
            num_cores=2,
            max_mem_gb=4.0,
            num_hosts=1,
            submit_time=datetime_to_str(job_start - timedelta(minutes=5)),
            start_time=datetime_to_str(job_start),
            finish_time=datetime_to_str(job_end)
        )
        
        # Process the job through the hourly bucketing
        start_time = job_start.timestamp()
        end_time = job_end.timestamp()
        round_hour = int(start_time // SECONDS_PER_HOUR)
        total_hourly_rate = 0.1 * job.num_hosts
        num_cores = 2
        
        hours_processed = []
        
        # Process each hour the job spans
        round_hour_seconds = round_hour * SECONDS_PER_HOUR
        
        while round_hour_seconds < end_time:
            next_round_hour = round_hour + 1
            next_round_hour_seconds = next_round_hour * SECONDS_PER_HOUR
            
            if round_hour_seconds <= start_time < next_round_hour_seconds:
                if end_time <= next_round_hour_seconds:
                    runtime_minutes = (end_time - start_time) / 60
                else:
                    runtime_minutes = (next_round_hour_seconds - start_time) / 60
            elif start_time <= round_hour_seconds and end_time > next_round_hour_seconds:
                runtime_minutes = 60
            elif start_time < round_hour_seconds and end_time <= next_round_hour_seconds:
                runtime_minutes = (end_time - round_hour_seconds) / 60
            else:
                runtime_minutes = 0
                
            instance_minutes = runtime_minutes * job.num_hosts
            core_hours = runtime_minutes * job.num_hosts * num_cores / 60
            
            analyzer._update_hourly_stats(
                round_hour=round_hour,
                instance_minutes_within_hour=instance_minutes,
                minutes_within_hour=runtime_minutes,
                core_hours=core_hours,
                total_cost_per_hour=total_hourly_rate,
                spot=False,
                instance_family='c7a'
            )
            
            hours_processed.append(round_hour)
            
            round_hour += 1
            round_hour_seconds = round_hour * SECONDS_PER_HOUR
        
        # All processed hours should be in hourly_stats (not filtered)
        for hour in hours_processed:
            self.assertIn(hour, analyzer.hourly_stats,
                         f"Hour {hour} within time range should be included")
        
        # Verify we have at least one hour
        self.assertGreater(len(hours_processed), 0,
                          "Job within time range should process at least one hour")


if __name__ == '__main__':
    unittest.main()

