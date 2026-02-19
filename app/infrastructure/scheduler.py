# app/infrastructure/scheduler.py
"""
Scheduler service for automated job execution.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.executors.threadpool import ThreadPoolExecutor
from typing import Dict, Any, Optional, Callable
import asyncio
from datetime import datetime

from app.config.settings import get_config
from app.infrastructure.logger import get_logger
from app.infrastructure.database import get_db_manager, JobExecution, JobLog
from app.core.base_job import JobResult, JobStatus

logger = get_logger("scheduler")


class JobScheduler:
    """Centralized job scheduler."""

    def __init__(self):
        self.config = get_config()
        self.scheduler = None
        self.job_registry: Dict[str, Dict[str, Any]] = {}
        self._running = False

    def initialize(self):
        """Initialize the scheduler."""
        if self.scheduler is not None:
            return

        jobstores = {
            'default': MemoryJobStore()
        }

        executors = {
            'default': ThreadPoolExecutor(max_workers=10),
            'async': AsyncIOExecutor()
        }

        job_defaults = self.config.scheduler.job_defaults

        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=self.config.scheduler.timezone
        )

        logger.info("Scheduler initialized")

    def start(self):
        """Start the scheduler."""
        if self.scheduler is None:
            self.initialize()

        if not self._running:
            self.scheduler.start()
            self._running = True
            logger.info("Scheduler started")

    def stop(self):
        """Stop the scheduler."""
        if self.scheduler and self._running:
            self.scheduler.shutdown(wait=True)
            self._running = False
            logger.info("Scheduler stopped")

    def add_job(
        self,
        job_id: str,
        job_class,
        branch_id: str = "default",
        trigger: str = "interval",
        **trigger_args
    ):
        """
        Add a job to the scheduler.

        Args:
            job_id: Unique job identifier
            job_class: Job class to instantiate
            branch_id: Branch identifier
            trigger: Trigger type ('interval', 'cron')
            **trigger_args: Trigger arguments
        """
        if self.scheduler is None:
            self.initialize()

        # Create trigger
        if trigger == "interval":
            job_trigger = IntervalTrigger(**trigger_args)
        elif trigger == "cron":
            job_trigger = CronTrigger(**trigger_args)
        else:
            raise ValueError(f"Unsupported trigger type: {trigger}")

        # Store job info
        self.job_registry[job_id] = {
            'job_class': job_class,
            'branch_id': branch_id,
            'trigger': trigger,
            'trigger_args': trigger_args
        }

        # Add to scheduler
        self.scheduler.add_job(
            func=self._execute_job,
            trigger=job_trigger,
            id=job_id,
            args=[job_id],
            name=f"{job_class.__name__} ({branch_id})",
            replace_existing=True
        )

        logger.info(f"Job {job_id} added to scheduler")

    def remove_job(self, job_id: str):
        """Remove a job from the scheduler."""
        if self.scheduler and self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            self.job_registry.pop(job_id, None)
            logger.info(f"Job {job_id} removed from scheduler")

    def run_job_now(self, job_id: str) -> Optional[JobResult]:
        """
        Run a job immediately.

        Args:
            job_id: Job identifier

        Returns:
            JobResult if job exists, None otherwise
        """
        if job_id not in self.job_registry:
            logger.warning(f"Job {job_id} not found in registry")
            return None

        return self._execute_job(job_id)

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status."""
        if self.scheduler is None:
            return None

        job = self.scheduler.get_job(job_id)
        if not job:
            return None

        return {
            'id': job.id,
            'name': job.name,
            'next_run_time': job.next_run_time,
            'trigger': str(job.trigger)
        }

    def list_jobs(self) -> Dict[str, Dict[str, Any]]:
        """List all scheduled jobs."""
        if self.scheduler is None:
            return {}

        jobs = {}
        for job in self.scheduler.get_jobs():
            jobs[job.id] = {
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time,
                'trigger': str(job.trigger)
            }
        return jobs

    def _execute_job(self, job_id: str) -> JobResult:
        """Execute a scheduled job."""
        if job_id not in self.job_registry:
            logger.error(f"Job {job_id} not found in registry")
            return JobResult(success=False, error="Job not found")

        job_info = self.job_registry[job_id]
        job_class = job_info['job_class']
        branch_id = job_info['branch_id']

        try:
            # Create job instance
            config = self.config.branches.get(branch_id, self.config.branches['default'])
            job = job_class(f"{job_class.__name__}_{branch_id}", config.__dict__, branch_id)

            # Execute job
            result = job.execute()

            # Store execution result in database
            self._store_execution_result(job_id, branch_id, result)

            return result

        except Exception as e:
            logger.error(f"Failed to execute job {job_id}: {e}", exc_info=True)
            result = JobResult(success=False, error=str(e))
            self._store_execution_result(job_id, branch_id, result)
            return result

    def _store_execution_result(self, job_id: str, branch_id: str, result: JobResult):
        """Store job execution result in database."""
        try:
            db_manager = get_db_manager()
            with db_manager.get_session() as session:
                # Create execution record
                execution = JobExecution(
                    job_name=job_id,
                    branch_id=branch_id,
                    status=result.status.value,
                    success=result.success,
                    error_message=result.error,
                    execution_time=result.execution_time,
                    retry_count=result.retry_count,
                    metrics=result.metrics
                )
                session.add(execution)
                session.flush()  # Get execution ID

                # Add logs if available
                if hasattr(result, 'logs'):
                    for log_entry in result.logs:
                        log_record = JobLog(
                            execution_id=execution.id,
                            level=log_entry.get('level', 'INFO'),
                            message=log_entry.get('message', ''),
                            timestamp=log_entry.get('timestamp', datetime.utcnow())
                        )
                        session.add(log_record)

                session.commit()

        except Exception as e:
            logger.error(f"Failed to store execution result: {e}")


# Global scheduler instance
_scheduler = None

def get_scheduler() -> JobScheduler:
    """Get the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = JobScheduler()
    return _scheduler