# app/infrastructure/scheduler.py
"""
APScheduler infrastructure for job scheduling.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from typing import Dict, Any, Optional, Callable
import logging

logger = logging.getLogger(__name__)


class JobScheduler:
    """APScheduler wrapper for job management."""

    def __init__(self):
        self.scheduler = None
        self._is_running = False

    def initialize(self):
        """Initialize the scheduler."""
        if self.scheduler:
            return

        jobstores = {
            'default': MemoryJobStore()
        }
        # Use ThreadPoolExecutor for synchronous execution
        executors = {
            'default': {'type': 'threadpool', 'max_workers': 10}
        }
        job_defaults = {
            'coalesce': True,
            'max_instances': 1,
            'misfire_grace_time': 30
        }

        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='UTC'
        )

        logger.info("Scheduler initialized")

    def start(self):
        """Start the scheduler."""
        if not self.scheduler:
            self.initialize()

        if not self._is_running:
            self.scheduler.start()
            self._is_running = True
            logger.info("Scheduler started")

    def stop(self):
        """Stop the scheduler."""
        if self.scheduler and self._is_running:
            self.scheduler.shutdown(wait=True)
            self._is_running = False
            logger.info("Scheduler stopped")

    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._is_running and self.scheduler and self.scheduler.running

    def add_job(self, job_id: str, func: Callable, trigger: str = "interval",
                minutes: int = 60, **kwargs):
        """Add a job to the scheduler."""
        if not self.scheduler:
            raise RuntimeError("Scheduler not initialized")

        if trigger == "interval":
            trigger_obj = IntervalTrigger(minutes=minutes)
        elif trigger == "cron":
            trigger_obj = CronTrigger(**kwargs)
        elif trigger == "date":
            trigger_obj = DateTrigger(**kwargs)
        else:
            raise ValueError(f"Unsupported trigger type: {trigger}")

        self.scheduler.add_job(
            func,
            trigger=trigger_obj,
            id=job_id,
            name=job_id,
            replace_existing=True
        )

        logger.info(f"Job added: {job_id}")

    def remove_job(self, job_id: str):
        """Remove a job from the scheduler."""
        if self.scheduler:
            self.scheduler.remove_job(job_id)
            logger.info(f"Job removed: {job_id}")

    def get_jobs(self) -> Dict[str, Any]:
        """Get all scheduled jobs."""
        if not self.scheduler:
            return {}

        jobs = {}
        for job in self._scheduler.get_jobs():
            jobs[job.id] = {
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            }
        return jobs

    def pause_job(self, job_id: str):
        """Pause a job."""
        if self.scheduler:
            self.scheduler.pause_job(job_id)
            logger.info(f"Job paused: {job_id}")

    def resume_job(self, job_id: str):
        """Resume a job."""
        if self.scheduler:
            self.scheduler.resume_job(job_id)
            logger.info(f"Job resumed: {job_id}")


# Global instance
_scheduler = None

def get_scheduler() -> JobScheduler:
    """Get the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = JobScheduler()
    return _scheduler