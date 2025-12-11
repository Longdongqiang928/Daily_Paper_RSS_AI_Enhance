"""
Centralized logging configuration for the arXiv RSS Zotero project.
This module provides a unified logging system with file and console handlers.

Usage:
    from logger_config import get_logger
    
    logger = get_logger(__name__)
    logger.info("This is an info message")
    logger.debug("This is a debug message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")

Features:
    - Automatic log file rotation (10MB max size, 5 backup files)
    - Date-based log file naming (e.g., module_name_2025-10-31.log)
    - Detailed file logs with line numbers and timestamps
    - Simplified console output for better readability
    - Configurable log levels via LOG_LEVEL environment variable
    - UTF-8 encoding support for international characters

Log Levels:
    - DEBUG: Detailed information for debugging
    - INFO: General informational messages
    - WARNING: Warning messages for potential issues
    - ERROR: Error messages for failures
    - CRITICAL: Critical errors that may cause application failure

Log File Location:
    All log files are stored in the 'logs/' directory
    Format: {module_name}_{YYYY-MM-DD}.log

Environment Variables:
    LOG_LEVEL: Set the default logging level (default: INFO)
               Example: SET LOG_LEVEL=DEBUG
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler

from config import config


class LoggerConfig:
    """
    Centralized logger configuration class.
    Creates both file and console handlers with appropriate formatting.
    """
    
    _initialized = False
    _loggers = {}
    
    @classmethod
    def setup_logger(
        cls,
        name: str,
        log_level: str = "INFO",
        log_dir: str = "logs",
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        console_output: bool = True
    ) -> logging.Logger:
        """
        Set up a logger with file and console handlers.
        
        Args:
            name: Logger name (typically module name)
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_dir: Directory to store log files
            max_bytes: Maximum size of each log file before rotation
            backup_count: Number of backup log files to keep
            console_output: Whether to output logs to console
            
        Returns:
            Configured logger instance
        """
        # Return existing logger if already configured
        if name in cls._loggers:
            return cls._loggers[name]
        
        # Create logger
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, log_level.upper()))
        logger.propagate = False
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Create log directory if it doesn't exist
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            fmt='[%(asctime)s] [%(name)s] [%(levelname)s] [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        simple_formatter = logging.Formatter(
            fmt='[%(asctime)s] [%(levelname)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # File handler with rotation
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = log_path / f"{name}_{today}.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
        
        # Console handler
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(getattr(logging, log_level.upper()))
            console_handler.setFormatter(simple_formatter)
            logger.addHandler(console_handler)
        
        # Store logger reference
        cls._loggers[name] = logger
        
        return logger
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get an existing logger or create a new one with default settings.
        
        Args:
            name: Logger name
            
        Returns:
            Logger instance
        """
        if name in cls._loggers:
            return cls._loggers[name]
        return cls.setup_logger(name)
    
    @classmethod
    def set_log_level(cls, name: str, level: str):
        """
        Change the log level for an existing logger.
        
        Args:
            name: Logger name
            level: New logging level
        """
        if name in cls._loggers:
            cls._loggers[name].setLevel(getattr(logging, level.upper()))
            for handler in cls._loggers[name].handlers:
                if isinstance(handler, logging.StreamHandler) and not isinstance(handler, RotatingFileHandler):
                    handler.setLevel(getattr(logging, level.upper()))


def get_logger(name: str, log_level: str | None = None) -> logging.Logger:
    """
    Convenience function to get a logger instance.
    
    Args:
        name: Logger name (typically __name__)
        log_level: Optional log level override
        
    Returns:
        Configured logger instance
    """
    # Get log level from environment variable or use default
    if log_level is None:
        log_level = config.LOG_LEVEL
    
    return LoggerConfig.setup_logger(name, log_level=log_level)
