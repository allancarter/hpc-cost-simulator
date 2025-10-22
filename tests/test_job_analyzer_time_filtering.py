#!/usr/bin/env python3
'''
Focused tests for JobAnalyzer time filtering logic
Tests jobs that start before starttime and end after endtime

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
'''

import unittest
from unittest.mock import MagicMock, Mock, patch
from datetime import datetime, timedelta, timezone
import sys
import os

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

from SchedulerJobInfo import datetime_to_str, str_to_datetime
from JobAnalyzerBase import SECONDS_PER_HOUR


class MockJobAnalyzer:
    """Mock JobAnalyzer that only implements the time filtering logic"""

    def __init__(self, starttime_str, endtime_str):
        self._starttime = starttime_str
        self._endtime = endtime_str

        if self._starttime:
            self._starttime_dt = str_to_datetime(self._starttime)
        else:
            self._starttime_dt = None

        if self._endtime:
            self._endtime_dt = str_to_datetime(self._endtime)
        else:
            self._endtime_dt = None

        self.hourly_stats = {}
        self.total_stats = {
            'on_demand': {
                'total': 0,
                'instance_hours': 0,
                'instance_families': {},
                'core_hours': {}
            },
            'spot': {
                'total': 0,
                'instance_hours': 0,
                'instance_families': {},
                'core_hours': {}
            },
            'instance_hours': 0
        }

    def _init_hourly_stats_hour(self, round_hour):
        """Initialize hourly stats for a specific hour"""
        self.hourly_stats[round_hour] = {
            'on_demand': {
                'total': 0,
                'instance_hours': 0,
                'core_hours': {}
            },
            'spot': {
                'total': 0,
                'instance_hours': 0,
                'core_hours': {}
            }
        }

    def _update_hourly_stats(self, round_hour: int, instance_minutes_within_hour: float,
                            minutes_within_hour: float, core_hours: float,
                            total_cost_per_hour: float, spot: bool, instance_family: str) -> None:
        """
        Update the hourly stats dict with a portion of the cost of a job that fits within a round hour.
        This is a simplified version of the real _update_hourly_stats method that focuses on time filtering.
        """
        round_hour = int(round_hour)

        # This is the key filtering logic we're testing
        if self._starttime:
            if round_hour * SECONDS_PER_HOUR < self._starttime_dt.timestamp():
                # Skip hours before starttime
                return

        if self._endtime:
            if round_hour * SECONDS_PER_HOUR > self._endtime_dt.timestamp():
                # Skip hours after endtime
                return

        # If we get here, the hour is within the time range
        if round_hour not in self.hourly_stats:
            self._init_hourly_stats_hour(round_hour)

        purchase_option = 'spot' if spot else 'on_demand'
        cost = minutes_within_hour / 60 * total_cost_per_hour

        self.hourly_stats[round_hour][purchase_option]['total'] += cost
        self.hourly_stats[round_hour][purchase_option][instance_family] = \
            cost + self.hourly_stats[round_hour][purchase_option].get(instance_family, 0)
        self.hourly_stats[round_hour][purchase_option]['core_hours'][instance_family] = \
            self.hourly_stats[round_hour][purchase_option]['core_hours'].get(instance_family, 0) + core_hours
        self.hourly_stats[round_hour][purchase_option]['instance_hours'] += instance_minutes_within_hour / 60

        self.total_stats[purchase_option]['instance_families'][instance_family] = \
            cost + self.total_stats[purchase_option]['instance_families'].get(instance_family, 0)
        self.total_stats[purchase_option]['instance_hours'] += instance_minutes_within_hour / 60
        self.total_stats['instance_hours'] += instance_minutes_within_hour / 60


class TestJobAnalyzerTimeFiltering(unittest.TestCase):
    """Test cases for time filtering in _update_hourly_stats"""

    def setUp(self):
        """Set up test fixtures"""
        # Set up test time window
        # Start: 2024-01-01 10:00:00
        # End:   2024-01-01 12:00:00
        self.start_datetime = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        self.end_datetime = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        self.starttime_str = datetime_to_str(self.start_datetime)
        self.endtime_str = datetime_to_str(self.end_datetime)

    def test_update_hourly_stats_before_starttime(self):
        """Test that hours before starttime are filtered out"""
        analyzer = MockJobAnalyzer(self.starttime_str, self.endtime_str)

        # Get the hour before starttime
        before_starttime_hour = int(self.start_datetime.timestamp() // SECONDS_PER_HOUR) - 1

        # Try to update stats for an hour before starttime
        analyzer._update_hourly_stats(
            round_hour=before_starttime_hour,
            instance_minutes_within_hour=60.0,
            minutes_within_hour=60.0,
            core_hours=2.0,
            total_cost_per_hour=0.1,
            spot=False,
            instance_family='c7a'
        )

        # Verify that the hour was NOT added
        self.assertNotIn(before_starttime_hour, analyzer.hourly_stats,
                        "Hour before starttime should be filtered out")
        self.assertEqual(len(analyzer.hourly_stats), 0,
                        "No hours should be in hourly_stats")

    def test_update_hourly_stats_after_endtime(self):
        """Test that hours after endtime are filtered out"""
        analyzer = MockJobAnalyzer(self.starttime_str, self.endtime_str)

        # Get the hour after endtime
        after_endtime_hour = int(self.end_datetime.timestamp() // SECONDS_PER_HOUR) + 1

        # Try to update stats for an hour after endtime
        analyzer._update_hourly_stats(
            round_hour=after_endtime_hour,
            instance_minutes_within_hour=60.0,
            minutes_within_hour=60.0,
            core_hours=2.0,
            total_cost_per_hour=0.1,
            spot=False,
            instance_family='c7a'
        )

        # Verify that the hour was NOT added
        self.assertNotIn(after_endtime_hour, analyzer.hourly_stats,
                        "Hour after endtime should be filtered out")
        self.assertEqual(len(analyzer.hourly_stats), 0,
                        "No hours should be in hourly_stats")

    def test_update_hourly_stats_within_time_range(self):
        """Test that hours within the time range are included"""
        analyzer = MockJobAnalyzer(self.starttime_str, self.endtime_str)

        # Get an hour within the time range
        within_range_hour = int(self.start_datetime.timestamp() // SECONDS_PER_HOUR)

        # Update stats for an hour within range
        analyzer._update_hourly_stats(
            round_hour=within_range_hour,
            instance_minutes_within_hour=60.0,
            minutes_within_hour=60.0,
            core_hours=2.0,
            total_cost_per_hour=0.1,
            spot=False,
            instance_family='c7a'
        )

        # Verify that the hour WAS added
        self.assertIn(within_range_hour, analyzer.hourly_stats,
                     "Hour within time range should be included")

        # Verify the cost was calculated correctly
        expected_cost = 60.0 / 60 * 0.1
        self.assertAlmostEqual(
            analyzer.hourly_stats[within_range_hour]['on_demand']['total'],
            expected_cost,
            places=6
        )

    def test_job_spanning_before_starttime_to_within_range(self):
        """Test a job that starts before starttime and ends within the time range

        This simulates what happens when _process_hourly_jobs breaks down a job
        that starts before the time window but ends within it.
        """
        analyzer = MockJobAnalyzer(self.starttime_str, self.endtime_str)

        # Job starts 1 hour before starttime and ends 30 minutes after starttime
        job_start = self.start_datetime - timedelta(hours=1)
        job_end = self.start_datetime + timedelta(minutes=30)

        # Simulate processing the job hour by hour
        start_time = job_start.timestamp()
        end_time = job_end.timestamp()
        round_hour = int(start_time // SECONDS_PER_HOUR)

        hours_processed = []
        round_hour_seconds = round_hour * SECONDS_PER_HOUR

        while round_hour_seconds < end_time:
            next_round_hour = round_hour + 1
            next_round_hour_seconds = next_round_hour * SECONDS_PER_HOUR

            # Calculate runtime for this hour
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

            analyzer._update_hourly_stats(
                round_hour=round_hour,
                instance_minutes_within_hour=runtime_minutes,
                minutes_within_hour=runtime_minutes,
                core_hours=runtime_minutes * 2 / 60,
                total_cost_per_hour=0.1,
                spot=False,
                instance_family='c7a'
            )

            hours_processed.append(round_hour)
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
        """Test a job that starts before starttime and ends after endtime

        This is the main test case: a long-running job that completely spans
        the analysis time window.
        """
        analyzer = MockJobAnalyzer(self.starttime_str, self.endtime_str)

        # Job starts 1 hour before starttime and ends 1 hour after endtime
        job_start = self.start_datetime - timedelta(hours=1)
        job_end = self.end_datetime + timedelta(hours=1)

        # Simulate processing the job hour by hour
        start_time = job_start.timestamp()
        end_time = job_end.timestamp()
        round_hour = int(start_time // SECONDS_PER_HOUR)

        round_hour_seconds = round_hour * SECONDS_PER_HOUR

        while round_hour_seconds < end_time:
            next_round_hour = round_hour + 1
            next_round_hour_seconds = next_round_hour * SECONDS_PER_HOUR

            # Calculate runtime for this hour
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

            analyzer._update_hourly_stats(
                round_hour=round_hour,
                instance_minutes_within_hour=runtime_minutes,
                minutes_within_hour=runtime_minutes,
                core_hours=runtime_minutes * 4 / 60,
                total_cost_per_hour=0.2,
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

        # Verify that only hours within the time window are included
        expected_hours = set()
        current_hour = int(self.start_datetime.timestamp() // SECONDS_PER_HOUR)
        end_hour = int(self.end_datetime.timestamp() // SECONDS_PER_HOUR)
        while current_hour <= end_hour:
            expected_hours.add(current_hour)
            current_hour += 1

        actual_hours = set(analyzer.hourly_stats.keys())
        self.assertEqual(actual_hours, expected_hours,
                        "Only hours within time window should be included")

    def test_job_within_range_to_after_endtime(self):
        """Test a job that starts within the time range and ends after endtime"""
        analyzer = MockJobAnalyzer(self.starttime_str, self.endtime_str)

        # Job starts 30 minutes after starttime and ends 1 hour after endtime
        job_start = self.start_datetime + timedelta(minutes=30)
        job_end = self.end_datetime + timedelta(hours=1)

        # Simulate processing the job hour by hour
        start_time = job_start.timestamp()
        end_time = job_end.timestamp()
        round_hour = int(start_time // SECONDS_PER_HOUR)

        round_hour_seconds = round_hour * SECONDS_PER_HOUR

        while round_hour_seconds < end_time:
            next_round_hour = round_hour + 1
            next_round_hour_seconds = next_round_hour * SECONDS_PER_HOUR

            # Calculate runtime for this hour
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

            analyzer._update_hourly_stats(
                round_hour=round_hour,
                instance_minutes_within_hour=runtime_minutes,
                minutes_within_hour=runtime_minutes,
                core_hours=runtime_minutes * 2 / 60,
                total_cost_per_hour=0.1,
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

    def test_no_time_filters(self):
        """Test that when no time filters are set, all hours are included"""
        analyzer = MockJobAnalyzer(starttime_str=None, endtime_str=None)

        # Try various hours - they should all be included
        test_hours = [100, 200, 300, 400, 500]

        for hour in test_hours:
            analyzer._update_hourly_stats(
                round_hour=hour,
                instance_minutes_within_hour=60.0,
                minutes_within_hour=60.0,
                core_hours=2.0,
                total_cost_per_hour=0.1,
                spot=False,
                instance_family='c7a'
            )

        # All hours should be included when no filters are set
        for hour in test_hours:
            self.assertIn(hour, analyzer.hourly_stats,
                         f"Hour {hour} should be included when no time filters are set")

    def test_only_starttime_filter(self):
        """Test filtering with only starttime set (no endtime)"""
        analyzer = MockJobAnalyzer(starttime_str=self.starttime_str, endtime_str=None)

        before_hour = int(self.start_datetime.timestamp() // SECONDS_PER_HOUR) - 1
        at_start_hour = int(self.start_datetime.timestamp() // SECONDS_PER_HOUR)
        after_hour = int(self.start_datetime.timestamp() // SECONDS_PER_HOUR) + 10

        # Try hours before, at, and after starttime
        for hour in [before_hour, at_start_hour, after_hour]:
            analyzer._update_hourly_stats(
                round_hour=hour,
                instance_minutes_within_hour=60.0,
                minutes_within_hour=60.0,
                core_hours=2.0,
                total_cost_per_hour=0.1,
                spot=False,
                instance_family='c7a'
            )

        # Hour before starttime should be filtered
        self.assertNotIn(before_hour, analyzer.hourly_stats,
                        "Hour before starttime should be filtered out")

        # Hours at and after starttime should be included
        self.assertIn(at_start_hour, analyzer.hourly_stats,
                     "Hour at starttime should be included")
        self.assertIn(after_hour, analyzer.hourly_stats,
                     "Hour after starttime should be included when no endtime is set")

    def test_only_endtime_filter(self):
        """Test filtering with only endtime set (no starttime)"""
        analyzer = MockJobAnalyzer(starttime_str=None, endtime_str=self.endtime_str)

        before_hour = int(self.end_datetime.timestamp() // SECONDS_PER_HOUR) - 10
        at_end_hour = int(self.end_datetime.timestamp() // SECONDS_PER_HOUR)
        after_hour = int(self.end_datetime.timestamp() // SECONDS_PER_HOUR) + 1

        # Try hours before, at, and after endtime
        for hour in [before_hour, at_end_hour, after_hour]:
            analyzer._update_hourly_stats(
                round_hour=hour,
                instance_minutes_within_hour=60.0,
                minutes_within_hour=60.0,
                core_hours=2.0,
                total_cost_per_hour=0.1,
                spot=False,
                instance_family='c7a'
            )

        # Hours before and at endtime should be included
        self.assertIn(before_hour, analyzer.hourly_stats,
                     "Hour before endtime should be included when no starttime is set")
        self.assertIn(at_end_hour, analyzer.hourly_stats,
                     "Hour at endtime should be included")

        # Hour after endtime should be filtered
        self.assertNotIn(after_hour, analyzer.hourly_stats,
                        "Hour after endtime should be filtered out")


if __name__ == '__main__':
    unittest.main()
