# app/infrastructure/scheduler_bootstrap.py
"""
Scheduler bootstrap for HET IT Control System.
Initializes and configures the job scheduler.
"""

import logging
from typing import Dict, Any, Callable
from app.infrastructure.scheduler import get_scheduler
from app.infrastructure.logging import get_service_logger

logger = get_service_logger()

def bootstrap_scheduler() -> None:
    """Bootstrap the job scheduler with default jobs."""
    scheduler = get_scheduler()

    try:
        # Initialize scheduler
        scheduler.initialize()
        logger.info("Scheduler bootstrap initialized")

        # Add default system jobs
        _add_system_jobs(scheduler)

        # Start scheduler
        scheduler.start()
        logger.info("Scheduler bootstrap completed")

    except Exception as e:
        logger.error(f"Scheduler bootstrap failed: {e}")
        raise

def _add_system_jobs(scheduler) -> None:
    """Add default system maintenance jobs."""
    # Database backup job - daily at 2 AM
    scheduler.add_job(
        "daily_db_backup",
        _database_backup_job,
        trigger="cron",
        hour=2,
        minute=0
    )
    logger.info("Daily database backup job scheduled")

    # Log cleanup job - weekly on Sunday at 3 AM
    scheduler.add_job(
        "weekly_log_cleanup",
        _log_cleanup_job,
        trigger="cron",
        day_of_week="sun",
        hour=3,
        minute=0
    )
    logger.info("Weekly log cleanup job scheduled")

    # System health check - every 30 minutes
    scheduler.add_job(
        "system_health_check",
        _system_health_check,
        trigger="interval",
        minutes=30
    )
    logger.info("System health check job scheduled")

def _database_backup_job() -> None:
    """Perform daily database backup."""
    try:
        from app.infrastructure.database import get_database_manager
        db_manager = get_database_manager()
        db_manager.create_backup()
        logger.info("Database backup completed")
    except Exception as e:
        logger.error(f"Database backup failed: {e}")

def _log_cleanup_job() -> None:
    """Clean up old log files."""
    try:
        import shutil
        from pathlib import Path

        log_dir = Path("logs")
        if log_dir.exists():
            # Remove log files older than 30 days
            import time
            current_time = time.time()
            max_age = 30 * 24 * 60 * 60  # 30 days in seconds

            for log_file in log_dir.glob("*.log*"):
                if log_file.stat().st_mtime < (current_time - max_age):
                    log_file.unlink()
                    logger.info(f"Removed old log file: {log_file}")

        logger.info("Log cleanup completed")
    except Exception as e:
        logger.error(f"Log cleanup failed: {e}")

def _system_health_check() -> None:
    """Perform system health check."""
    try:
        from app.infrastructure.database import get_database_manager
        db_manager = get_database_manager()

        # Check database connectivity
        db_size = db_manager.get_db_size()
        logger.info(f"System health check: Database size {db_size} bytes")

        # Check scheduler status
        scheduler = get_scheduler()
        if scheduler.is_running():
            logger.info("System health check: Scheduler running")
        else:
            logger.warning("System health check: Scheduler not running")

    except Exception as e:
        logger.error(f"System health check failed: {e}")

def shutdown_scheduler() -> None:
    """Shutdown the scheduler gracefully."""
    try:
        scheduler = get_scheduler()
        scheduler.stop()
        logger.info("Scheduler shutdown completed")
    except Exception as e:
        logger.error(f"Scheduler shutdown failed: {e}")