# app/core/base_job.py
"""
Base job class for all automation jobs in the HET IT Control System.
"""
import abc
import time
import logging
from typing import Any, Dict, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from app.infrastructure.exceptions import JobError, ValidationError
from app.infrastructure.logger import get_logger


class JobStatus(Enum):
    """Job execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class JobResult:
    """Result of job execution."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    status: JobStatus = JobStatus.SUCCESS
    retry_count: int = 0
    metrics: Dict[str, Any] = field(default_factory=dict)


class BaseJob(abc.ABC):
    """
    Base class for all automation jobs.

    Provides common functionality:
    - Retry mechanism
    - Timeout protection
    - Structured logging
    - Execution metrics
    - State management
    - Error handling
    """

    def __init__(self, name: str, config: Dict[str, Any], branch_id: str = "default"):
        """
        Initialize the job.

        Args:
            name: Job name
            config: Job configuration
            branch_id: Branch identifier
        """
        self.name = name
        self.config = config
        self.branch_id = branch_id
        self.logger = get_logger(f"job.{name}")

        # Job settings
        self._timeout = config.get('timeout', 300)  # 5 minutes default
        self._max_retries = config.get('max_retries', 3)
        self._retry_delay = config.get('retry_delay', 5)
        self._retry_backoff = config.get('retry_backoff', 2.0)

        # Status tracking
        self._status = JobStatus.PENDING
        self._start_time: Optional[float] = None
        self._progress_callback: Optional[Callable[[str, float], None]] = None

    @property
    def status(self) -> JobStatus:
        """Get current job status."""
        return self._status

    def set_progress_callback(self, callback: Callable[[str, float], None]) -> None:
        """Set progress callback function."""
        self._progress_callback = callback

    def update_progress(self, message: str, progress: float = 0.0) -> None:
        """Update job progress."""
        if self._progress_callback:
            self._progress_callback(message, progress)

    @abc.abstractmethod
    def validate(self) -> bool:
        """
        Validate job prerequisites and configuration.

        Returns:
            True if validation passes, False otherwise
        """
        pass

    @abc.abstractmethod
    def run(self) -> JobResult:
        """
        Execute the job logic.

        Returns:
            JobResult with execution outcome
        """
        pass

    def handle_error(self, error: Exception) -> None:
        """
        Handle job-specific errors.

        Args:
            error: The exception that occurred
        """
        self.logger.error(f"Job {self.name} failed: {error}", exc_info=True)

    def update_status(self, status: JobStatus, message: str = "") -> None:
        """
        Update job status.

        Args:
            status: New status
            message: Status message
        """
        self._status = status
        level = logging.INFO if status == JobStatus.SUCCESS else logging.ERROR
        self.logger.log(level, f"Job {self.name} status: {status.value} - {message}")

    def log_result(self, result: JobResult) -> None:
        """
        Log job execution result.

        Args:
            result: Job execution result
        """
        if result.success:
            self.logger.info(
                f"Job {self.name} completed successfully in {result.execution_time:.2f}s"
            )
        else:
            self.logger.error(
                f"Job {self.name} failed after {result.execution_time:.2f}s: {result.error}"
            )

    def execute(self) -> JobResult:
        """
        Execute job with retry logic and timeout protection.

        Returns:
            JobResult with final outcome
        """
        self._start_time = time.time()
        self.update_status(JobStatus.RUNNING, "Starting execution")

        # Validation
        if not self.validate():
            result = JobResult(
                success=False,
                error="Validation failed",
                execution_time=time.time() - self._start_time,
                status=JobStatus.FAILED
            )
            self.update_status(JobStatus.FAILED, "Validation failed")
            self.log_result(result)
            return result

        # Execute with retries
        retry_count = 0
        while retry_count <= self._max_retries:
            try:
                self.logger.info(f"Executing job {self.name} (attempt {retry_count + 1})")

                # Execute with timeout
                import signal
                import threading

                result = [None]
                exception = [None]

                def target():
                    try:
                        result[0] = self.run()
                    except Exception as e:
                        exception[0] = e

                thread = threading.Thread(target=target, daemon=True)
                thread.start()
                thread.join(timeout=self._timeout)

                if thread.is_alive():
                    # Timeout occurred
                    self.logger.warning(f"Job {self.name} timed out after {self._timeout}s")
                    result_obj = JobResult(
                        success=False,
                        error=f"Timeout after {self._timeout} seconds",
                        execution_time=time.time() - self._start_time,
                        status=JobStatus.TIMEOUT,
                        retry_count=retry_count
                    )
                    self.update_status(JobStatus.TIMEOUT, "Execution timed out")
                    self.log_result(result_obj)
                    return result_obj

                if exception[0]:
                    raise exception[0]

                job_result = result[0]
                job_result.execution_time = time.time() - self._start_time
                job_result.retry_count = retry_count

                if job_result.success:
                    self.update_status(JobStatus.SUCCESS, "Completed successfully")
                else:
                    self.update_status(JobStatus.FAILED, job_result.error or "Unknown error")

                self.log_result(job_result)
                return job_result

            except Exception as e:
                self.handle_error(e)
                retry_count += 1

                if retry_count <= self._max_retries:
                    delay = self._retry_delay * (self._retry_backoff ** (retry_count - 1))
                    self.logger.info(f"Retrying job {self.name} in {delay:.1f}s (attempt {retry_count + 1})")
                    time.sleep(delay)
                else:
                    result = JobResult(
                        success=False,
                        error=str(e),
                        execution_time=time.time() - self._start_time,
                        status=JobStatus.FAILED,
                        retry_count=retry_count
                    )
                    self.update_status(JobStatus.FAILED, f"Failed after {retry_count} retries")
                    self.log_result(result)
                    return result

        # Should not reach here
        return JobResult(
            success=False,
            error="Unexpected execution end",
            execution_time=time.time() - self._start_time,
            status=JobStatus.FAILED
        )


class StatefulJob(BaseJob):
    """
    Base class for jobs that maintain state between runs.
    """

    def __init__(self, name: str, config: Dict[str, Any], branch_id: str = "default"):
        super().__init__(name, config, branch_id)
        self.state_file = config.get('state_file')

    def load_state(self) -> Dict[str, Any]:
        """
        Load job state from file.

        Returns:
            Job state dictionary
        """
        if not self.state_file or not self.state_file.exists():
            return {}
        try:
            import json
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.warning(f"Failed to load state: {e}")
            return {}

    def save_state(self, state: Dict[str, Any]) -> None:
        """
        Save job state to file.

        Args:
            state: State dictionary to save
        """
        if not self.state_file:
            return
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            import json
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")