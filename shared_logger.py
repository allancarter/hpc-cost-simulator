#!/usr/bin/env python3
'''
Shared logger configuration for JobAnalyzer and JobAnalyzerBase

This module provides a centralized logger configuration that writes to:
- stdout (INFO and above)
- stderr (WARNING and above)
- FileHandler (when configured)

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
'''

import logging
import sys

# Create the main logger
logger = logging.getLogger('JobAnalyzer')
logger.propagate = False
logger.setLevel(logging.INFO)

# Create formatter
logger_formatter = logging.Formatter('%(levelname)s:%(asctime)s: %(message)s')

# StreamHandler for stdout (INFO and above)
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setFormatter(logger_formatter)
stdout_handler.setLevel(logging.INFO)
stdout_handler.addFilter(lambda record: record.levelno < logging.WARNING)
logger.addHandler(stdout_handler)

# StreamHandler for stderr (WARNING and above)
stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setFormatter(logger_formatter)
stderr_handler.setLevel(logging.WARNING)
logger.addHandler(stderr_handler)

# FileHandler will be added by add_file_handler() function
_file_handler = None

def add_file_handler(log_file_name):
    """
    Add a file handler to the shared logger
    
    Args:
        log_file_name (str): Path to the log file
    """
    global _file_handler
    if _file_handler:
        # Remove existing file handler if present
        logger.removeHandler(_file_handler)
    
    _file_handler = logging.FileHandler(filename=log_file_name)
    _file_handler.setFormatter(logger_formatter)
    logger.addHandler(_file_handler)
    logger.info(f"Logging to file: {log_file_name}")

def get_logger():
    """
    Get the shared logger instance
    
    Returns:
        logging.Logger: The shared logger
    """
    return logger










