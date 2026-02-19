# app/infrastructure/logger.py
"""
Centralized logging configuration for the HET IT Control System.
"""
import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

from app.config.settings import get_config


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name

    Returns:
        Configured logger
    """
    return logging.getLogger(f"het_it_control.{name}")


def setup_logging(
    log_level: str = None,
    log_dir: Path = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> None:
    """
    Setup centralized logging configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
        max_bytes: Maximum log file size
        backup_count: Number of backup files to keep
    """
    config = get_config()

    if log_level is None:
        log_level = config.logging.level
    if log_dir is None:
        log_dir = config.paths.logs_dir

    log_dir.mkdir(parents=True, exist_ok=True)

    # Convert log level string to logging level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Create formatters
    detailed_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    simple_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Root logger
    root_logger = logging.getLogger("het_it_control")
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)

    # Info log file handler (rotating)
    info_handler = logging.handlers.RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8"
    )
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(info_handler)

    # Error log file handler (rotating)
    error_handler = logging.handlers.RotatingFileHandler(
        log_dir / "error.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)

    # Job-specific log handler
    job_handler = logging.handlers.RotatingFileHandler(
        log_dir / "jobs.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8"
    )
    job_handler.setLevel(logging.DEBUG)
    job_handler.setFormatter(detailed_formatter)
    job_handler.addFilter(lambda record: record.name.startswith("het_it_control.job"))
    root_logger.addHandler(job_handler)

    # Database log handler
    db_handler = logging.handlers.RotatingFileHandler(
        log_dir / "database.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8"
    )
    db_handler.setLevel(logging.DEBUG)
    db_handler.setFormatter(detailed_formatter)
    db_handler.addFilter(lambda record: record.name.startswith("het_it_control.database"))
    root_logger.addHandler(db_handler)


class JobFilter(logging.Filter):
    """Filter for job-specific logs."""
    def filter(self, record):
        return "job" in record.name


def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
    """
    Handle uncaught exceptions by logging them.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger = get_logger("uncaught")
    logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


# Set global exception handler
sys.excepthook = handle_uncaught_exception