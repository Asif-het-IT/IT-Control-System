# app/core/job.py
"""
Core job entity and base classes for HET IT Control System.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from uuid import UUID, uuid4


class JobStatus(Enum):
    """Job execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class JobResult:
    """Result of a job execution."""
    success: bool
    message: str = ""
    data: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        if self.error and not self.message:
            self.message = self.error


class BaseJob:
    """Base class for all jobs in the system."""

    def __init__(self, name: str = None, config: Optional[Dict[str, Any]] = None):
        self.name = name or self.__class__.__name__.lower().replace('job', '')
        self.config = config or {}
        self.job_id = str(uuid4())

    def validate(self) -> bool:
        """Validate job configuration before execution."""
        return True

    def run(self) -> JobResult:
        """Execute the job. Must be implemented by subclasses."""
        raise NotImplementedError

    def execute(self) -> JobResult:
        """Execute job with timing and error handling."""
        start_time = datetime.utcnow()

        try:
            if not self.validate():
                return JobResult(
                    success=False,
                    error="Job validation failed",
                    execution_time=0.0
                )

            result = self.run()

            if not isinstance(result, JobResult):
                result = JobResult(success=True, data=result, message="Job completed")

            result.execution_time = (datetime.utcnow() - start_time).total_seconds()
            return result

        except Exception as e:
            return JobResult(
                success=False,
                error=str(e),
                execution_time=(datetime.utcnow() - start_time).total_seconds()
            )
<parameter name="filePath">d:\My App\app\core\job.py