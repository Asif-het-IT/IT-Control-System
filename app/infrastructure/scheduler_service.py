# app/infrastructure/scheduler_service.py
"""
Enterprise Scheduler Service (APScheduler)
✅ BackgroundScheduler singleton
✅ Supports:
   - Run Once (DateTrigger)
   - Daily / Weekly / Cron (CronTrigger)
✅ Job replace/update
✅ Next run lookup
✅ Unschedule
"""

from __future__ import annotations
from typing import Callable, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

PROJECT_ROOT = Path(__file__).resolve().parents[2]
JOBSTORE_DB = PROJECT_ROOT / "database" / "scheduler_jobs.sqlite"


_scheduler: Optional[BackgroundScheduler] = None


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler

    JOBSTORE_DB.parent.mkdir(parents=True, exist_ok=True)

    jobstores = {
        "default": SQLAlchemyJobStore(url=f"sqlite:///{JOBSTORE_DB}")
    }

    _scheduler = BackgroundScheduler(jobstores=jobstores)
    _scheduler.start(paused=False)
    return _scheduler


def schedule_run_once(job_id: str, func: Callable[[], Any], run_dt: datetime) -> None:
    sch = get_scheduler()
    sch.add_job(
        func=func,
        trigger=DateTrigger(run_date=run_dt),
        id=job_id,
        replace_existing=True,
        misfire_grace_time=60
    )


def schedule_daily(job_id: str, func: Callable[[], Any], hour: int, minute: int) -> None:
    sch = get_scheduler()
    sch.add_job(
        func=func,
        trigger=CronTrigger(hour=hour, minute=minute),
        id=job_id,
        replace_existing=True,
        misfire_grace_time=120
    )


def schedule_weekly(job_id: str, func: Callable[[], Any], day_of_week: str, hour: int, minute: int) -> None:
    """
    day_of_week: mon,tue,wed,thu,fri,sat,sun
    """
    sch = get_scheduler()
    sch.add_job(
        func=func,
        trigger=CronTrigger(day_of_week=day_of_week, hour=hour, minute=minute),
        id=job_id,
        replace_existing=True,
        misfire_grace_time=120
    )


def schedule_cron(job_id: str, func: Callable[[], Any], cron_expr: str) -> None:
    """
    cron_expr format: "m h dom mon dow"
    Example: "0 9 * * *"
    """
    parts = cron_expr.split()
    if len(parts) != 5:
        raise ValueError("Cron must be 5 parts: minute hour day month dow (e.g. 0 9 * * *)")

    minute, hour, day, month, dow = parts
    sch = get_scheduler()
    sch.add_job(
        func=func,
        trigger=CronTrigger(minute=minute, hour=hour, day=day, month=month, day_of_week=dow),
        id=job_id,
        replace_existing=True,
        misfire_grace_time=120
    )


def unschedule(job_id: str) -> None:
    sch = get_scheduler()
    try:
        sch.remove_job(job_id)
    except Exception:
        pass


def get_next_run(job_id: str) -> Optional[str]:
    sch = get_scheduler()
    job = sch.get_job(job_id)
    if not job or not job.next_run_time:
        return None
    # Display format
    return job.next_run_time.strftime("%Y-%m-%d %H:%M:%S")


def list_schedules() -> Dict[str, str]:
    sch = get_scheduler()
    out: Dict[str, str] = {}
    for j in sch.get_jobs():
        out[j.id] = j.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if j.next_run_time else "-"
    return out