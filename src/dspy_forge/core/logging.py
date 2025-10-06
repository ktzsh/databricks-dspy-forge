import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    Setup application logging configuration
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for logging output
        format_string: Custom format string for log messages
    
    Returns:
        Configured logger instance
    """
    
    # Default format if none provided
    if format_string is None:
        format_string = (
            "%(asctime)s - %(name)s - %(levelname)s - "
            "%(filename)s:%(lineno)d - %(message)s"
        )

    # Get root logger
    logger = logging.getLogger()

    # Set the logger level
    logger.setLevel(getattr(logging, level.upper()))
    logging.getLogger('databricks.sql').setLevel(logging.WARNING)
    logging.getLogger('databricks.sdk').setLevel(logging.WARNING)

    if log_file:
        # If log file is specified, clear existing handlers and create new ones
        logger.handlers.clear()

        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, level.upper()))
        console_formatter = logging.Formatter(format_string, datefmt="%Y-%m-%d %H:%M:%S")
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # Create file handler
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, level.upper()))
        file_formatter = logging.Formatter(format_string, datefmt="%Y-%m-%d %H:%M:%S")
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    else:
        # If no log file, just update existing handlers with new formatting
        formatter = logging.Formatter(format_string, datefmt="%Y-%m-%d %H:%M:%S")

        # Update all existing handlers with new formatter and level
        for handler in logger.handlers:
            handler.setFormatter(formatter)
            handler.setLevel(getattr(logging, level.upper()))
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name"""
    return logging.getLogger(name)