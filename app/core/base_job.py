# app/core/base_job.py
"""
Stable BaseJob for HET IT Control System
- Minimal + compatible with your existing job files
"""

from __future__ import annotations
import abc
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class JobResult:
    success: bool
    message: str = ""
    data: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    status: JobStatus = field(init=False)

    def __post_init__(self):
        # Auto-set status based on success
        self.status = JobStatus.SUCCESS if self.success else JobStatus.FAILED

        # Ensure message is set if error exists
        if self.error and not self.message:
            self.message = self.error


class BaseJob(abc.ABC):
    """
    Enterprise BaseJob with flexible constructor for backward compatibility.
    Supports both new style: BaseJob(name, config, branch_id)
    And legacy style: BaseJob() with manual setup
    """

    def __init__(self, name: str = None, config: Optional[Dict[str, Any]] = None, branch_id: str = None):
        # Flexible constructor for backward compatibility
        if name is None:
            # Legacy mode - will be set by subclass or externally
            self.name = self.__class__.__name__.lower().replace('job', '')
        else:
            self.name = name

        self.config = config or {}
        self.branch_id = branch_id or "default"

        # Auto-setup for legacy classes that don't call super()
        if hasattr(self, '_setup_legacy') and callable(self._setup_legacy):
            self._setup_legacy()

    @abc.abstractmethod
    def validate(self) -> bool:
        return True

    @abc.abstractmethod
    def run(self) -> JobResult:
        raise NotImplementedError

    def execute(self) -> JobResult:
        start = time.time()

        try:
            if not self.validate():
                return JobResult(
                    success=False,
                    error="Validation failed",
                    execution_time=time.time() - start,
                    status=JobStatus.FAILED,
                )

            result = self.run()
            if not isinstance(result, JobResult):
                # Safety: job returned raw value
                result = JobResult(success=True, data=result, message="Job completed")

            result.execution_time = time.time() - start
            result.status = JobStatus.SUCCESS if result.success else JobStatus.FAILED
            return result

        except Exception as e:
            return JobResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start,
                status=JobStatus.FAILED,
            )