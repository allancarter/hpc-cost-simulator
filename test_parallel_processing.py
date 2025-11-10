#!/usr/bin/env python3
"""
Test script for parallel processing functionality

This script creates sample jobs.csv files and tests the parallel processing capabilities.
"""

import csv
import os
import shutil
import sys
from datetime import datetime, timedelta

def create_test_csv(filename, start_date, num_jobs=100):
    """Create a test jobs.csv file with sample data"""
    print(f"Creating test file: {filename} with {num_jobs} jobs")
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow([
            'Job id', 'Num Hosts', 'Start time', 'Run time (seconds)', 
            'Wait time (seconds)', 'Num Cores', 'Max Mem (GB)', 'Project', 'Queue'
        ])
        
        # Write sample jobs
        current_time = start_date
        for i in range(num_jobs):
            job_id = f"job_{i+1}"
            num_hosts = 1
            start_time = current_time.strftime('%Y-%m-%d %H:%M:%S')
            run_time = 3600 + (i * 10)  # 1 hour + incremental
            wait_time = 300  # 5 minutes
            num_cores = 4
            max_mem_gb = 16.0
            project = "test_project"
            queue = "normal"
            
            writer.writerow([
                job_id, num_hosts, start_time, run_time, wait_time,
                num_cores, max_mem_gb, project, queue
            ])
            
            # Increment time for next job
            current_time += timedelta(minutes=30)

def create_test_environment():
    """Create test directory structure and sample CSV files"""
    print("Creating test environment...")
    
    # Create test directories
    test_dir = "test_parallel_data"
    if os.path.exists(test_dir):
        print(f"Removing existing test directory: {test_dir}")
        shutil.rmtree(test_dir)
    
    os.makedirs(test_dir)
    output_dir = "test_parallel_output"
    if os.path.exists(output_dir):
        print(f"Removing existing output directory: {output_dir}")
        shutil.rmtree(output_dir)
    
    # Create sample CSV files
    start_date = datetime(2024, 1, 1, 0, 0, 0)
    
    csv_files = []
    for i in range(3):
        filename = os.path.join(test_dir, f"jobs_batch_{i+1}.csv")
        create_test_csv(filename, start_date + timedelta(days=i*7), num_jobs=50)
        csv_files.append(filename)
    
    print(f"\nCreated {len(csv_files)} test CSV files in {test_dir}/")
    print(f"Output will be written to {output_dir}/")
    
    return test_dir, output_dir, csv_files

def print_test_commands(test_dir, output_dir):
    """Print example commands to test the functionality"""
    print("\n" + "="*80)
    print("TEST COMMANDS")
    print("="*80)
    
    print("\nIMPORTANT: You must source setup.sh first to activate the Python environment:")
    print("   source setup.sh")
    
    print("\n1. Test single file processing:")
    print(f"   ./JobAnalyzer.py --config config.yml --output-dir {output_dir} \\")
    print(f"     process_jobs_csv --input-jobs-csv {test_dir}/jobs_batch_1.csv")
    
    print("\n2. Test parallel processing:")
    print(f"   ./JobAnalyzer.py --config config.yml --output-dir {output_dir} \\")
    print(f"     parallel_jobs_csv --jobs-csv-dir {test_dir} --num-processes 2")
    
    print("\n3. Test with helper script (automatically sources setup.sh):")
    print(f"   ./parallel_jobs_processor.sh --jobs-csv-dir {test_dir} \\")
    print(f"     --output-dir {output_dir} --num-processes 2")
    
    print("\n4. Test combining hourly files:")
    print(f"   ./JobAnalyzer.py --config config.yml --output-dir {output_dir} \\")
    print(f"     combine_hourly")
    
    print("\n" + "="*80)
    print("\nNote: Make sure config.yml exists and is properly configured")
    print("="*80 + "\n")

def verify_output(output_dir):
    """Verify that output files were created"""
    print("\nVerifying output...")
    
    hourly_files_dir = os.path.join(output_dir, 'hourly-files')
    
    if not os.path.exists(hourly_files_dir):
        print(f"❌ ERROR: Hourly files directory not found: {hourly_files_dir}")
        return False
    
    # Check for batch subdirectories
    subdirs = [d for d in os.listdir(hourly_files_dir) 
               if os.path.isdir(os.path.join(hourly_files_dir, d)) 
               and d.startswith('batch_')]
    
    print(f"✓ Found {len(subdirs)} batch subdirectories")
    
    # Check for combined hourly files
    combined_files = [f for f in os.listdir(hourly_files_dir) 
                     if f.startswith('hourly-') and f.endswith('.csv')]
    
    print(f"✓ Found {len(combined_files)} combined hourly files")
    
    # Check for statistics files
    stats_csv = os.path.join(output_dir, 'hourly_stats.csv')
    stats_xlsx = os.path.join(output_dir, 'hourly_stats.xlsx')
    
    if os.path.exists(stats_csv):
        print(f"✓ Statistics CSV file created: {stats_csv}")
    else:
        print(f"⚠ Statistics CSV file not found: {stats_csv}")
    
    if os.path.exists(stats_xlsx):
        print(f"✓ Statistics Excel file created: {stats_xlsx}")
    else:
        print(f"⚠ Statistics Excel file not found: {stats_xlsx}")
    
    return True

def main():
    """Main test function"""
    print("="*80)
    print("JobAnalyzer Parallel Processing Test Setup")
    print("="*80)
    
    # Check if config.yml exists
    if not os.path.exists('config.yml'):
        print("\n⚠ WARNING: config.yml not found in current directory")
        print("You may need to create or specify a config file for actual testing")
    
    # Create test environment
    test_dir, output_dir, csv_files = create_test_environment()
    
    # Print test commands
    print_test_commands(test_dir, output_dir)
    
    print("\nTest data setup complete!")
    print("\nTo run the actual tests, execute the commands shown above.")
    print("\nTo clean up test data:")
    print(f"  rm -rf {test_dir} {output_dir}")

if __name__ == '__main__':
    main()
