# app/infrastructure/logger.py
"""
Production-grade structured logging configuration for the HET IT Control System.
Features:
- JSON structured logging for production
- Specialized loggers for different components
- Log rotation and compression
- Performance monitoring
- Error tracking with context
"""
import logging
import logging.handlers
import sys
import json
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

# Default log directory (will be overridden by setup_logging)
try:
    log_dir = Path(__file__).resolve().parent.parent.parent / "logs"
except NameError:
    # __file__ not defined (e.g., in PyInstaller spec analysis)
    import os
    log_dir = Path(os.getcwd()) / "logs"
max_bytes = 10 * 1024 * 1024  # 10MB
backup_count = 5


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Create base log entry
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "thread_name": record.threadName,
            "process": record.process,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record
        if hasattr(record, "__dict__"):
            for key, value in record.__dict__.items():
                if key not in {
                    'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                    'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                    'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                    'thread', 'threadName', 'processName', 'process', 'message'
                }:
                    log_entry[key] = value

        return json.dumps(log_entry, default=str)


class PerformanceFormatter(logging.Formatter):
    """Formatter for performance monitoring logs."""

    def format(self, record: logging.LogRecord) -> str:
        """Format performance log record."""
        duration = getattr(record, 'duration', None)
        memory_usage = getattr(record, 'memory_usage', None)
        cpu_usage = getattr(record, 'cpu_usage', None)

        if duration is not None:
            duration_str = f"{duration:.3f}s"
        else:
            duration_str = "N/A"

        perf_info = f"[PERF] Duration: {duration_str}"
        if memory_usage is not None:
            perf_info += f", Memory: {memory_usage:.1f}MB"
        if cpu_usage is not None:
            perf_info += f", CPU: {cpu_usage:.1f}%"

        return f"{super().format(record)} {perf_info}"


# Default performance formatter
performance_formatter = PerformanceFormatter()

# Default root logger
root_logger = logging.getLogger("het_it_control")


class ComponentLogger:
    """Specialized logger for different system components."""

    def __init__(self, component_name: str):
        self.component_name = component_name
        self.logger = logging.getLogger(f"het_it_control.{component_name}")
        self._metrics = threading.local()

    def start_operation(self, operation: str, **context) -> str:
        """Start timing an operation."""
        operation_id = f"{operation}_{threading.current_thread().ident}_{time.time()}"
        self._metrics.operation_id = operation_id
        self._metrics.start_time = time.time()
        self._metrics.operation = operation
        self._metrics.context = context

        self.logger.info(f"Starting operation: {operation}",
                        extra={"operation": operation, "operation_id": operation_id, **context})
        return operation_id

    def end_operation(self, operation_id: str, success: bool = True, **additional_context):
        """End timing an operation."""
        if not hasattr(self._metrics, 'start_time'):
            self.logger.warning(f"End operation called without start: {operation_id}")
            return

        duration = time.time() - self._metrics.start_time
        operation = getattr(self._metrics, 'operation', 'unknown')
        context = getattr(self._metrics, 'context', {})

        log_level = logging.INFO if success else logging.ERROR
        status = "completed" if success else "failed"

        self.logger.log(log_level, f"Operation {status}: {operation}",
                        extra={
                            "operation": operation,
                            "operation_id": operation_id,
                            "duration": duration,
                            "success": success,
                            **context,
                            **additional_context
                        })

        # Clean up
        delattr(self._metrics, 'operation_id')
        delattr(self._metrics, 'start_time')
        delattr(self._metrics, 'operation')
        delattr(self._metrics, 'context')

    def log_error(self, error: Exception, **context):
        """Log an error with full context."""
        self.logger.error(f"Error in {self.component_name}: {str(error)}",
                         exc_info=True, extra={"error_type": type(error).__name__, **context})

    def log_performance(self, operation: str, duration: float, **metrics):
        """Log performance metrics."""
        self.logger.info(f"Performance: {operation}",
                        extra={"operation": operation, "duration": duration, **metrics})


# Global logger instances
_scheduler_logger = None
_job_logger = None
_database_logger = None
_monitoring_logger = None
_gui_logger = None

def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name

    Returns:
        Configured logger
    """
    return logging.getLogger(f"het_it_control.{name}")


def get_scheduler_logger() -> ComponentLogger:
    """Get the specialized scheduler logger."""
    global _scheduler_logger
    if _scheduler_logger is None:
        _scheduler_logger = ComponentLogger("scheduler")
    return _scheduler_logger


def get_job_logger() -> ComponentLogger:
    """Get the specialized job logger."""
    global _job_logger
    if _job_logger is None:
        _job_logger = ComponentLogger("job")
    return _job_logger


def get_database_logger() -> ComponentLogger:
    """Get the specialized database logger."""
    global _database_logger
    if _database_logger is None:
        _database_logger = ComponentLogger("database")
    return _database_logger


def get_monitoring_logger() -> ComponentLogger:
    """Get the specialized monitoring logger."""
    global _monitoring_logger
    if _monitoring_logger is None:
        _monitoring_logger = ComponentLogger("monitoring")
    return _monitoring_logger


def get_gui_logger() -> ComponentLogger:
    """Get the specialized GUI logger."""
    global _gui_logger
    if _gui_logger is None:
        _gui_logger = ComponentLogger("gui")
    return _gui_logger


def setup_logging(
    log_level: str = None,
    log_dir: Path = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    json_format: bool = True
) -> None:
    """
    Setup centralized logging configuration with JSON support.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
        max_bytes: Maximum log file size
        backup_count: Number of backup files to keep
        json_format: Whether to use JSON formatting for production
    """
    from app.config.settings import get_config
    config = get_config()

    if log_level is None:
        log_level = config.logging.level
    if log_dir is None:
        log_dir = config.paths.logs_dir

    log_dir.mkdir(parents=True, exist_ok=True)

    # Convert log level string to logging level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Create formatters
    if json_format and config.environment == "production":
        detailed_formatter = JSONFormatter()
        simple_formatter = JSONFormatter()
        performance_formatter = JSONFormatter()
    else:
        detailed_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        simple_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        performance_formatter = PerformanceFormatter(
            "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s",
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

    # Application log file handler (rotating)
    app_handler = logging.handlers.RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8"
    )
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(app_handler)

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

    # Performance monitoring log handler
    perf_handler = logging.handlers.RotatingFileHandler(
        log_dir / "performance.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8"
    )
    perf_handler.setLevel(logging.INFO)
    perf_handler.setFormatter(performance_formatter)
    perf_handler.addFilter(lambda record: hasattr(record, 'duration') or hasattr(record, 'memory_usage'))
    root_logger.addHandler(perf_handler)

    # Scheduler log handler
    scheduler_handler = logging.handlers.RotatingFileHandler(
        log_dir / "scheduler.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8"
    )
    scheduler_handler.setLevel(logging.DEBUG)
    scheduler_handler.setFormatter(detailed_formatter)
    scheduler_handler.addFilter(lambda record: record.name.startswith("het_it_control.scheduler"))
    root_logger.addHandler(scheduler_handler)


class JobFilter(logging.Filter):
    """Filter for job-specific logs."""
    def filter(self, record):
        return "job" in record.name


def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
    """
    Handle uncaught exceptions by logging them with full context.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger = get_logger("uncaught")
    logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback),
                   extra={"exception_type": exc_type.__name__, "exception_message": str(exc_value)})


# Set global exception handler
sys.excepthook = handle_uncaught_exception


# Performance monitoring log handler - setup moved to setup_logging
# perf_handler = logging.handlers.RotatingFileHandler(
#     log_dir / "performance.log",
#     maxBytes=max_bytes,
#     backupCount=backup_count,
#     encoding="utf-8"
# )
# perf_handler.setLevel(logging.INFO)
# perf_handler.setFormatter(performance_formatter)
# perf_handler.addFilter(lambda record: hasattr(record, 'duration') or hasattr(record, 'memory_usage'))
# root_logger.addHandler(perf_handler)

# Scheduler log handler - setup moved to setup_logging
# scheduler_handler = logging.handlers.RotatingFileHandler(
#     log_dir / "scheduler.log",
#     maxBytes=max_bytes,
#     backupCount=backup_count,
#     encoding="utf-8"
# )
# scheduler_handler.setLevel(logging.DEBUG)
# scheduler_handler.setFormatter(detailed_formatter)
# scheduler_handler.addFilter(lambda record: record.name.startswith("het_it_control.scheduler"))
# root_logger.addHandler(scheduler_handler)


class JobFilter(logging.Filter):
    """Filter for job-specific logs."""
    def filter(self, record):
        return "job" in record.name


def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
    """
    Handle uncaught exceptions by logging them with full context.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger = get_logger("uncaught")
    logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback),
                   extra={"exception_type": exc_type.__name__, "exception_message": str(exc_value)})


# Set global exception handler
sys.excepthook = handle_uncaught_exception