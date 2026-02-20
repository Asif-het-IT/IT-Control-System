# app/domain/entities.py
"""
Domain entities for HET IT Control System.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4


@dataclass
class Job:
    """Job entity."""
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    job_type: str = ""
    config: dict = field(default_factory=dict)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Schedule:
    """Job schedule entity."""
    id: UUID = field(default_factory=uuid4)
    job_id: UUID
    schedule_type: str = "daily"  # once, daily, weekly, cron
    cron_expression: Optional[str] = None
    start_time: Optional[str] = None
    is_active: bool = True
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ExecutionRecord:
    """Job execution record."""
    id: UUID = field(default_factory=uuid4)
    job_id: UUID
    schedule_id: Optional[UUID] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    success: bool = False
    message: str = ""
    execution_time: float = 0.0
    error_message: Optional[str] = None
<parameter name="filePath">d:\My App\app\domain\entities.py