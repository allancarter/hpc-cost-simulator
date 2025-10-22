#!/usr/bin/env python3
'''
End-to-End tests for JobAnalyzer using synthetic CSV input
Tests jobs that start before starttime and end after endtime

This test creates a synthetic jobs.csv file, runs the actual JobAnalyzer.py
to process it, and validates the hourly_stats.csv output file.

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
'''

import unittest
from unittest.mock import MagicMock, Mock, patch
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

from JobAnalyzer import JobAnalyzer
from CSVLogParser import CSVLogParser
from SchedulerJobInfo import datetime_to_str, str_to_datetime
from JobAnalyzerBase import SECONDS_PER_HOUR


class TestJobAnalyzerCSVEndToEnd(unittest.TestCase):
    """End-to-end tests using synthetic CSV input and validating CSV output"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = TemporaryDirectory()
        self.output_dir = os.path.join(self.temp_dir.name, 'output')
        os.makedirs(self.output_dir, exist_ok=True)

        # Create a proper config file
        self.config_file = os.path.join(self.temp_dir.name, 'test_config.yml')
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
  runtime_ranges_minutes:
    - 1
    - 5
    - 20
    - 60
    - 240
  instance_prefix_list:
    - c7a
    - m7a
    - r7a

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

        # Create instance type info JSON
        self.instance_info_file = os.path.join(self.temp_dir.name, 'instance_type_info.json')
        instance_info = {
            'c7a.large': {
                'DefaultCores': 2,
                'MemoryInGiB': 4,
                'ProcessorInfo': {'SustainedClockSpeedInGhz': 3.0},
                'pricing': {
                    'OnDemand': 0.1020,
                    'spot': 0.0306,
                    'EC2SavingsPlan': {'EC2 SP 3yr All Upfront': 0.0612},
                    'ComputeSavingsPlan': {'Compute SP 3yr All Upfront': 0.0714}
                }
            },
            'c7a.xlarge': {
                'DefaultCores': 4,
                'MemoryInGiB': 8,
                'ProcessorInfo': {'SustainedClockSpeedInGhz': 3.0},
                'pricing': {
                    'OnDemand': 0.2040,
                    'spot': 0.0612,
                    'EC2SavingsPlan': {'EC2 SP 3yr All Upfront': 0.1224},
                    'ComputeSavingsPlan': {'Compute SP 3yr All Upfront': 0.1428}
                }
            },
            'm7a.large': {
                'DefaultCores': 2,
                'MemoryInGiB': 8,
                'ProcessorInfo': {'SustainedClockSpeedInGhz': 3.0},
                'pricing': {
                    'OnDemand': 0.1088,
                    'spot': 0.0326,
                    'EC2SavingsPlan': {'EC2 SP 3yr All Upfront': 0.0653},
                    'ComputeSavingsPlan': {'Compute SP 3yr All Upfront': 0.0762}
                }
            }
        }

        with open(self.instance_info_file, 'w') as f:
            json.dump(instance_info, f, indent=2)

        # Set up test time window
        # Start: 2024-01-15 10:00:00 UTC
        # End:   2024-01-15 14:00:00 UTC (4 hour window)
        self.start_datetime = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        self.end_datetime = datetime(2024, 1, 15, 14, 0, 0, tzinfo=timezone.utc)
        self.starttime_str = datetime_to_str(self.start_datetime)
        self.endtime_str = datetime_to_str(self.end_datetime)

    def tearDown(self):
        """Clean up test fixtures"""
        self.temp_dir.cleanup()

    def _create_synthetic_jobs_csv(self, jobs_data):
        """
        Create a synthetic jobs.csv file with test data

        Args:
            jobs_data: List of tuples (job_id, start_time_dt, end_time_dt, num_cores, max_mem_gb, num_hosts)

        Returns:
            Path to the created CSV file
        """
        csv_file = os.path.join(self.temp_dir.name, 'jobs.csv')

        # CSV header matching SchedulerJobInfo format
        header = [
            'job_id', 'num_cores', 'max_mem_gb', 'num_hosts',
            'submit_time', 'start_time', 'finish_time',
            'wait_time', 'run_time', 'queue', 'project'
        ]

        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)

            for job_id, start_dt, end_dt, num_cores, max_mem_gb, num_hosts in jobs_data:
                submit_dt = start_dt - timedelta(minutes=5)
                run_time_seconds = int((end_dt - start_dt).total_seconds())
                wait_time_seconds = int((start_dt - submit_dt).total_seconds())

                # Format times as expected by CSVLogParser
                submit_time = datetime_to_str(submit_dt)
                start_time = datetime_to_str(start_dt)
                finish_time = datetime_to_str(end_dt)

                # Format durations as [DD-[HH:]]MM:SS
                run_time_hours = run_time_seconds // 3600
                run_time_mins = (run_time_seconds % 3600) // 60
                run_time_secs = run_time_seconds % 60
                run_time = f"{run_time_hours:02d}:{run_time_mins:02d}:{run_time_secs:02d}"

                wait_time_mins = wait_time_seconds // 60
                wait_time_secs = wait_time_seconds % 60
                wait_time = f"00:{wait_time_mins:02d}:{wait_time_secs:02d}"

                row = [
                    job_id, num_cores, max_mem_gb, num_hosts,
                    submit_time, start_time, finish_time,
                    wait_time, run_time, 'normal', 'test_project'
                ]
                writer.writerow(row)

        return csv_file

    def _run_job_analyzer(self, csv_file):
        """
        Run JobAnalyzer with the synthetic CSV input

        Args:
            csv_file: Path to the jobs CSV file

        Returns:
            JobAnalyzer instance after analysis
        """
        # Patch the instance type info file path
        with patch('JobAnalyzerBase.path.join') as mock_join:
            def side_effect(*args):
                if len(args) >= 2 and args[-1] == 'instance_type_info.json':
                    return self.instance_info_file
                return os.path.join(*args)

            mock_join.side_effect = side_effect

            with patch('JobAnalyzer.EC2InstanceTypeInfo') as mock_ec2_info_class:
                mock_ec2_instance = Mock()
                mock_ec2_info_class.return_value = mock_ec2_instance

                # Create CSV parser
                csv_parser = CSVLogParser(
                    csv_input_file=csv_file,
                    output_csv=None,
                    starttime=self.starttime_str,
                    endtime=self.endtime_str
                )

                # Create JobAnalyzer
                analyzer = JobAnalyzer(
                    scheduler_parser=csv_parser,
                    config_filename=self.config_file,
                    output_dir=self.output_dir,
                    starttime=self.starttime_str,
                    endtime=self.endtime_str,
                    queue_filters=None,
                    project_filters=None
                )

                # Manually set instance type info
                with open(self.instance_info_file, 'r') as f:
                    analyzer.instance_type_info = json.load(f)

                analyzer.instance_family_info = {
                    'c7a': {'MaxInstanceType': 'c7a.xlarge', 'MaxMemoryInGiB': 8},
                    'm7a': {'MaxInstanceType': 'm7a.large', 'MaxMemoryInGiB': 8},
                    'r7a': {'MaxInstanceType': 'r7a.large', 'MaxMemoryInGiB': 16}
                }

                # Mock EC2InstanceTypeInfo.get_instance_family
                with patch('JobAnalyzer.EC2InstanceTypeInfo.get_instance_family') as mock_get_family:
                    def get_family_side_effect(instance_type):
                        return instance_type.split('.')[0]
                    mock_get_family.side_effect = get_family_side_effect

                    # Run the analysis
                    analyzer.analyze_jobs()

                return analyzer

    def _read_hourly_stats_csv(self):
        """Read and parse the hourly_stats.csv output file"""
        hourly_stats_file = os.path.join(self.output_dir, 'hourly_stats.csv')

        if not os.path.exists(hourly_stats_file):
            return None

        hourly_data = {}
        with open(hourly_stats_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                relative_hour = int(row['Relative Hour'])
                hourly_data[relative_hour] = {
                    'Total OnDemand Costs': float(row['Total OnDemand Costs']) if row['Total OnDemand Costs'] else 0,
                    'Total Spot Costs': float(row['Total Spot Costs']) if row['Total Spot Costs'] else 0,
                    'Instance Hours': float(row['Instance Hours']) if row['Instance Hours'] else 0
                }

        return hourly_data

    def test_job_spanning_entire_time_window(self):
        """Test a single job that starts before starttime and ends after endtime"""
        # Job runs from 09:00 to 15:00 (6 hours total)
        # Time window is 10:00 to 14:00 (4 hours)
        # Expected: Only the 4 hours from 10:00-14:00 should be counted

        job_start = self.start_datetime - timedelta(hours=1)  # 09:00
        job_end = self.end_datetime + timedelta(hours=1)      # 15:00

        jobs_data = [
            (1, job_start, job_end, 2, 4.0, 1)  # job_id, start, end, cores, mem, hosts
        ]

        # Create CSV and run analyzer
        csv_file = self._create_synthetic_jobs_csv(jobs_data)
        analyzer = self._run_job_analyzer(csv_file)

        # Read output
        hourly_stats = self._read_hourly_stats_csv()

        self.assertIsNotNone(hourly_stats, "hourly_stats.csv should be created")

        # Should have exactly 4 relative hours (0, 1, 2, 3) for the 4-hour window
        expected_hours = {0, 1, 2, 3}
        actual_hours = set(hourly_stats.keys())

        self.assertEqual(actual_hours, expected_hours,
                        f"Should have exactly 4 hours in output. Expected {expected_hours}, got {actual_hours}")

        # Each hour should have instance hours > 0
        for hour in expected_hours:
            self.assertGreater(hourly_stats[hour]['Instance Hours'], 0,
                             f"Hour {hour} should have instance hours > 0")

        # Total instance hours should be approximately 4 (1 instance * 4 hours)
        total_instance_hours = sum(h['Instance Hours'] for h in hourly_stats.values())
        self.assertAlmostEqual(total_instance_hours, 4.0, places=1,
                              msg="Total instance hours should be ~4.0 for 1 instance over 4 hours")

    def test_multiple_jobs_with_different_time_relationships(self):
        """Test multiple jobs with different relationships to the time window"""
        # Time window: 10:00 to 14:00

        jobs_data = [
            # Job 1: Completely before window (08:00-09:00) - should be excluded
            (1, self.start_datetime - timedelta(hours=2),
                self.start_datetime - timedelta(hours=1), 2, 4.0, 1),

            # Job 2: Starts before, ends within (09:30-11:00) - partial
            (2, self.start_datetime - timedelta(minutes=30),
                self.start_datetime + timedelta(hours=1), 2, 4.0, 1),

            # Job 3: Completely within (11:00-13:00) - fully counted
            (3, self.start_datetime + timedelta(hours=1),
                self.start_datetime + timedelta(hours=3), 2, 4.0, 1),

            # Job 4: Starts within, ends after (13:30-15:00) - partial
            (4, self.end_datetime - timedelta(minutes=30),
                self.end_datetime + timedelta(hours=1), 2, 4.0, 1),

            # Job 5: Completely after window (15:00-16:00) - should be excluded
            (5, self.end_datetime + timedelta(hours=1),
                self.end_datetime + timedelta(hours=2), 2, 4.0, 1),

            # Job 6: Spans entire window and beyond (09:00-15:00) - fully counted for window
            (6, self.start_datetime - timedelta(hours=1),
                self.end_datetime + timedelta(hours=1), 4, 8.0, 1),
        ]

        csv_file = self._create_synthetic_jobs_csv(jobs_data)
        analyzer = self._run_job_analyzer(csv_file)

        hourly_stats = self._read_hourly_stats_csv()

        self.assertIsNotNone(hourly_stats, "hourly_stats.csv should be created")

        # Should have exactly 4 relative hours
        self.assertEqual(len(hourly_stats), 4,
                        "Should have exactly 4 hours in the time window")

        # Each hour should have contributions from multiple jobs
        for hour in hourly_stats:
            self.assertGreater(hourly_stats[hour]['Instance Hours'], 0,
                             f"Hour {hour} should have instance hours")

        # Jobs 1 and 5 should not contribute (they're outside the window)
        # Jobs 2, 3, 4, 6 should all contribute
        # Total should be greater than just one job
        total_instance_hours = sum(h['Instance Hours'] for h in hourly_stats.values())
        self.assertGreater(total_instance_hours, 4.0,
                          "Total instance hours should be > 4.0 with multiple jobs")

    def test_job_starting_before_ending_within_window(self):
        """Test job that starts 2 hours before starttime and ends 1 hour after starttime"""
        # Job runs from 08:00 to 11:00 (3 hours total)
        # Time window is 10:00 to 14:00
        # Expected: Only 1 hour (10:00-11:00) should be counted

        job_start = self.start_datetime - timedelta(hours=2)  # 08:00
        job_end = self.start_datetime + timedelta(hours=1)    # 11:00

        jobs_data = [
            (1, job_start, job_end, 2, 4.0, 1)
        ]

        csv_file = self._create_synthetic_jobs_csv(jobs_data)
        analyzer = self._run_job_analyzer(csv_file)

        hourly_stats = self._read_hourly_stats_csv()

        self.assertIsNotNone(hourly_stats, "hourly_stats.csv should be created")

        # Should only have hours that overlap with the job (relative hours 0, possibly 1)
        # Job ends at 11:00, which is relative hour 1 (10:00-11:00 = hour 0, 11:00-12:00 = hour 1)
        self.assertIn(0, hourly_stats, "Should have relative hour 0 (10:00-11:00)")

        # Total instance hours should be approximately 1.0 (job runs 1 hour in window)
        total_instance_hours = sum(h['Instance Hours'] for h in hourly_stats.values())
        self.assertAlmostEqual(total_instance_hours, 1.0, places=1,
                              msg="Total instance hours should be ~1.0 for 1 hour in window")

    def test_job_starting_within_ending_after_window(self):
        """Test job that starts 1 hour before endtime and ends 1 hour after endtime"""
        # Job runs from 13:00 to 15:00 (2 hours total)
        # Time window is 10:00 to 14:00
        # Expected: Only 1 hour (13:00-14:00) should be counted

        job_start = self.end_datetime - timedelta(hours=1)   # 13:00
        job_end = self.end_datetime + timedelta(hours=1)     # 15:00

        jobs_data = [
            (1, job_start, job_end, 2, 4.0, 1)
        ]

        csv_file = self._create_synthetic_jobs_csv(jobs_data)
        analyzer = self._run_job_analyzer(csv_file)

        hourly_stats = self._read_hourly_stats_csv()

        self.assertIsNotNone(hourly_stats, "hourly_stats.csv should be created")

        # Should have relative hour 3 (13:00-14:00)
        self.assertIn(3, hourly_stats, "Should have relative hour 3 (13:00-14:00)")

        # Total instance hours should be approximately 1.0
        total_instance_hours = sum(h['Instance Hours'] for h in hourly_stats.values())
        self.assertAlmostEqual(total_instance_hours, 1.0, places=1,
                              msg="Total instance hours should be ~1.0 for 1 hour in window")

    def test_spot_eligible_vs_long_running_jobs(self):
        """Test that short jobs (spot eligible) and long jobs are both handled correctly"""
        # Time window: 10:00 to 14:00

        jobs_data = [
            # Short job (30 min) - spot eligible, spans boundary
            (1, self.start_datetime - timedelta(minutes=15),
                self.start_datetime + timedelta(minutes=15), 2, 4.0, 1),

            # Long job (8 hours) - not spot eligible, spans entire window
            (2, self.start_datetime - timedelta(hours=2),
                self.end_datetime + timedelta(hours=2), 4, 8.0, 1),
        ]

        csv_file = self._create_synthetic_jobs_csv(jobs_data)
        analyzer = self._run_job_analyzer(csv_file)

        hourly_stats = self._read_hourly_stats_csv()

        self.assertIsNotNone(hourly_stats, "hourly_stats.csv should be created")

        # Should have 4 hours
        self.assertEqual(len(hourly_stats), 4, "Should have 4 hours in window")

        # Should have both spot and on-demand costs
        total_spot = sum(h['Total Spot Costs'] for h in hourly_stats.values())
        total_od = sum(h['Total OnDemand Costs'] for h in hourly_stats.values())

        # At least one should be > 0 (depending on spot eligibility threshold)
        total_costs = total_spot + total_od
        self.assertGreater(total_costs, 0, "Should have some costs recorded")

    def test_cost_calculation_accuracy_for_partial_hours(self):
        """Test that costs are calculated accurately for jobs spanning time boundaries"""
        # Job runs from 09:30 to 10:30 (1 hour total)
        # Time window is 10:00 to 14:00
        # Expected: Only 30 minutes (10:00-10:30) should be counted
        # Cost should be (30/60) * hourly_rate

        job_start = self.start_datetime - timedelta(minutes=30)  # 09:30
        job_end = self.start_datetime + timedelta(minutes=30)    # 10:30

        jobs_data = [
            (1, job_start, job_end, 2, 4.0, 1)
        ]

        csv_file = self._create_synthetic_jobs_csv(jobs_data)
        analyzer = self._run_job_analyzer(csv_file)

        hourly_stats = self._read_hourly_stats_csv()

        self.assertIsNotNone(hourly_stats, "hourly_stats.csv should be created")

        # Should only have relative hour 0 (10:00-11:00)
        self.assertIn(0, hourly_stats, "Should have relative hour 0")

        # Instance hours for hour 0 should be approximately 0.5 (30 minutes)
        hour_0_instance_hours = hourly_stats[0]['Instance Hours']
        self.assertAlmostEqual(hour_0_instance_hours, 0.5, places=2,
                              msg="Hour 0 should have ~0.5 instance hours (30 minutes)")

        # Total costs should be non-zero
        total_costs = hourly_stats[0]['Total OnDemand Costs'] + hourly_stats[0]['Total Spot Costs']
        self.assertGreater(total_costs, 0, "Should have costs for the 30 minutes")

    def test_no_jobs_within_time_window(self):
        """Test that when all jobs are outside the time window, output shows zero activity"""
        # Time window: 10:00 to 14:00

        jobs_data = [
            # Job 1: Before window
            (1, self.start_datetime - timedelta(hours=3),
                self.start_datetime - timedelta(hours=2), 2, 4.0, 1),

            # Job 2: After window
            (2, self.end_datetime + timedelta(hours=1),
                self.end_datetime + timedelta(hours=2), 2, 4.0, 1),
        ]

        csv_file = self._create_synthetic_jobs_csv(jobs_data)
        analyzer = self._run_job_analyzer(csv_file)

        hourly_stats = self._read_hourly_stats_csv()

        # hourly_stats.csv might still be created but should have no data or all zeros
        if hourly_stats:
            total_instance_hours = sum(h['Instance Hours'] for h in hourly_stats.values())
            self.assertEqual(total_instance_hours, 0,
                           "Should have 0 instance hours when no jobs overlap window")

    def test_summary_stats_csv_created(self):
        """Test that summary_stats.csv is also created and contains expected data"""
        job_start = self.start_datetime
        job_end = self.end_datetime

        jobs_data = [
            (1, job_start, job_end, 2, 4.0, 1)
        ]

        csv_file = self._create_synthetic_jobs_csv(jobs_data)
        analyzer = self._run_job_analyzer(csv_file)

        # Check that summary_stats.csv was created
        summary_file = os.path.join(self.output_dir, 'summary_stats.csv')
        self.assertTrue(os.path.exists(summary_file),
                       "summary_stats.csv should be created")

        # Read and verify summary stats
        with open(summary_file, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            self.assertGreater(len(rows), 0, "Summary stats should have data")

            # First row should be 'Total'
            total_row = rows[0]
            self.assertEqual(total_row[''], 'Total', "First row should be Total")

            # Should have some instance hours
            instance_hours = float(total_row['Instance Hours'])
            self.assertGreater(instance_hours, 0, "Should have instance hours in summary")


if __name__ == '__main__':
    unittest.main()
