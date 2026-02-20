# app/infrastructure/monitoring.py
"""
Enterprise-grade resource and system monitoring for the HET IT Control System.
Features:
- Real-time system metrics collection
- Job execution monitoring
- Scheduler health monitoring
- Alert integration
- Performance analytics
- Historical data tracking
"""

import psutil
import threading
import time
import platform
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import statistics
import logging

from app.config.settings import get_config
from app.infrastructure.logger import get_monitoring_logger
from app.infrastructure.exceptions import MonitoringError
from app.services.alert_manager import get_alert_manager, AlertSeverity

logger = get_monitoring_logger()


@dataclass
class ResourceMetrics:
    """Container for system resource metrics."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_percent: Dict[str, float] = field(default_factory=dict)
    disk_used_gb: Dict[str, float] = field(default_factory=dict)
    disk_free_gb: Dict[str, float] = field(default_factory=dict)
    network_bytes_sent: int = 0
    network_bytes_recv: int = 0
    process_count: int = 0
    thread_count: int = 0


@dataclass
class JobMetrics:
    """Container for job execution metrics."""
    job_id: str
    status: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    success: bool = False
    error_message: Optional[str] = None
    retry_count: int = 0
    branch: str = "default"


@dataclass
class SystemHealth:
    """System health assessment."""
    overall_status: str  # "healthy", "warning", "critical"
    cpu_status: str
    memory_status: str
    disk_status: str
    scheduler_status: str
    last_check: datetime
    issues: List[str] = field(default_factory=list)


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


class MonitoringService:
    """Enterprise-grade monitoring service."""

    def __init__(self):
        self.config = get_config()
        self.alert_manager = get_alert_manager()
        self.logger = get_monitoring_logger()

        # Monitoring state
        self._monitoring_active = False
        self._monitor_thread = None
        self._stop_event = threading.Event()

        # Metrics storage
        self._resource_history: List[ResourceMetrics] = []
        self._job_history: List[JobMetrics] = []
        self._max_history_size = 1000

        # Job monitoring
        self._active_jobs: Dict[str, JobMetrics] = {}
        self._job_lock = threading.RLock()

        # Scheduler monitoring
        self._last_scheduler_heartbeat = datetime.now()
        self._scheduler_healthy = True

        # Health monitoring
        self._last_health_check = datetime.now()
        self._current_health: Optional[SystemHealth] = None

        # Alert callbacks
        self._health_callbacks: List[Callable[[SystemHealth], None]] = []

        # Performance tracking
        self._last_network_counters = psutil.net_io_counters()

    def start_monitoring(self) -> None:
        """Start the monitoring service."""
        if self._monitoring_active:
            logger.warning("Monitoring service already active")
            return

        self._monitoring_active = True
        self._stop_event.clear()

        # Start monitoring thread
        self._monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            name="monitoring-service",
            daemon=True
        )
        self._monitor_thread.start()

        # Register alert callbacks
        self.alert_manager.add_alert_callback(self._handle_alert)

        logger.info("Monitoring service started")

    def stop_monitoring(self) -> None:
        """Stop the monitoring service."""
        if not self._monitoring_active:
            return

        self._monitoring_active = False
        self._stop_event.set()

        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5.0)

        logger.info("Monitoring service stopped")

    def add_health_callback(self, callback: Callable[[SystemHealth], None]) -> None:
        """Add health status callback."""
        self._health_callbacks.append(callback)

    def get_current_metrics(self) -> ResourceMetrics:
        """Get current system resource metrics."""
        return self._collect_resource_metrics()

    def get_resource_history(self, hours: int = 1) -> List[ResourceMetrics]:
        """Get resource metrics history."""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [m for m in self._resource_history if m.timestamp >= cutoff]

    def get_job_history(self, job_id: Optional[str] = None, limit: int = 50) -> List[JobMetrics]:
        """Get job execution history."""
        with self._job_lock:
            if job_id:
                jobs = [j for j in self._job_history if j.job_id == job_id]
            else:
                jobs = self._job_history.copy()

            return jobs[-limit:] if limit > 0 else jobs

    def get_job_statistics(self) -> Dict[str, Any]:
        """Get comprehensive job statistics."""
        with self._job_lock:
            if not self._job_history:
                return {}

            # Basic stats
            total_jobs = len(self._job_history)
            successful_jobs = len([j for j in self._job_history if j.success])
            failed_jobs = total_jobs - successful_jobs

            # Recent performance (last 24 hours)
            cutoff_24h = datetime.now() - timedelta(hours=24)
            recent_jobs = [j for j in self._job_history if j.end_time and j.end_time >= cutoff_24h]

            # Calculate averages
            completed_jobs = [j for j in self._job_history if j.duration is not None]
            avg_duration = statistics.mean([j.duration for j in completed_jobs]) if completed_jobs else 0

            # Job failure analysis
            job_failures = {}
            for job in self._job_history:
                if not job.success:
                    job_failures[job.job_id] = job_failures.get(job.job_id, 0) + 1

            most_failing_job = max(job_failures.items(), key=lambda x: x[1]) if job_failures else None

            # Failure trend (last 10 failures)
            recent_failures = [j for j in self._job_history if not j.success][-10:]

            return {
                "total_jobs": total_jobs,
                "successful_jobs": successful_jobs,
                "failed_jobs": failed_jobs,
                "success_rate": (successful_jobs / total_jobs * 100) if total_jobs > 0 else 0,
                "average_duration": avg_duration,
                "jobs_last_24h": len(recent_jobs),
                "job_failures": dict(sorted(job_failures.items(), key=lambda x: x[1], reverse=True)),
                "most_failing_job": most_failing_job,
                "recent_failures": [
                    {
                        "job_id": f.job_id,
                        "end_time": f.end_time.isoformat() if f.end_time else None,
                        "error_message": f.error_message,
                        "duration": f.duration
                    } for f in recent_failures
                ]
            }

    def get_system_health(self) -> SystemHealth:
        """Get current system health assessment."""
        return self._assess_health()

    def record_scheduler_heartbeat(self) -> None:
        """Record scheduler heartbeat."""
        self._last_scheduler_heartbeat = datetime.now()
        if not self._scheduler_healthy:
            self._scheduler_healthy = True
            logger.info("Scheduler heartbeat restored")

    def start_job_monitoring(self, job_id: str, branch: str = "default") -> None:
        """Start monitoring a job execution."""
        with self._job_lock:
            if job_id in self._active_jobs:
                logger.warning(f"Job {job_id} already being monitored")
                return

            metrics = JobMetrics(
                job_id=job_id,
                status="running",
                start_time=datetime.now(),
                branch=branch
            )
            self._active_jobs[job_id] = metrics

            logger.debug(f"Started monitoring job: {job_id}")

    def update_job_status(self, job_id: str, status: str, **kwargs) -> None:
        """Update job monitoring status."""
        with self._job_lock:
            if job_id not in self._active_jobs:
                logger.warning(f"Job {job_id} not being monitored")
                return

            job = self._active_jobs[job_id]
            job.status = status

            if status in ["completed", "failed"]:
                job.end_time = datetime.now()
                job.duration = (job.end_time - job.start_time).total_seconds() if job.start_time else 0
                job.success = status == "completed"

                if "error_message" in kwargs:
                    job.error_message = kwargs["error_message"]
                if "retry_count" in kwargs:
                    job.retry_count = kwargs["retry_count"]

                # Move to history
                self._job_history.append(job)
                if len(self._job_history) > self._max_history_size:
                    self._job_history.pop(0)

                del self._active_jobs[job_id]

                # Check for alert conditions
                self._check_job_alerts(job)

                logger.debug(f"Job monitoring completed: {job_id} ({status})")

    def get_active_jobs(self) -> List[JobMetrics]:
        """Get currently active jobs."""
        with self._job_lock:
            return list(self._active_jobs.values())

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics."""
        resource_history = self.get_resource_history(hours=1)

        if not resource_history:
            return {}

        # Calculate averages
        avg_cpu = statistics.mean([m.cpu_percent for m in resource_history])
        avg_memory = statistics.mean([m.memory_percent for m in resource_history])

        # Peak values
        peak_cpu = max([m.cpu_percent for m in resource_history])
        peak_memory = max([m.memory_percent for m in resource_history])

        # Network throughput (bytes per second average)
        if len(resource_history) > 1:
            time_diff = (resource_history[-1].timestamp - resource_history[0].timestamp).total_seconds()
            total_sent = sum([m.network_bytes_sent for m in resource_history])
            total_recv = sum([m.network_bytes_recv for m in resource_history])
            avg_sent_per_sec = total_sent / time_diff if time_diff > 0 else 0
            avg_recv_per_sec = total_recv / time_diff if time_diff > 0 else 0
        else:
            avg_sent_per_sec = avg_recv_per_sec = 0

        return {
            "average_cpu_percent": avg_cpu,
            "average_memory_percent": avg_memory,
            "peak_cpu_percent": peak_cpu,
            "peak_memory_percent": peak_memory,
            "average_network_sent_bps": avg_sent_per_sec,
            "average_network_recv_bps": avg_recv_per_sec,
            "process_count": resource_history[-1].process_count if resource_history else 0,
            "thread_count": resource_history[-1].thread_count if resource_history else 0,
            "monitoring_period_hours": 1
        }

    def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        logger.info("Monitoring loop started")

        while not self._stop_event.is_set():
            try:
                start_time = time.time()

                # Collect resource metrics
                metrics = self._collect_resource_metrics()
                self._resource_history.append(metrics)
                if len(self._resource_history) > self._max_history_size:
                    self._resource_history.pop(0)

                # Check scheduler health
                self._check_scheduler_health()

                # Assess overall health
                health = self._assess_health()
                if health != self._current_health:
                    self._current_health = health
                    self._notify_health_callbacks(health)

                # Check resource thresholds
                self._check_resource_thresholds(metrics)

                # Clean up old data periodically
                if len(self._resource_history) % 100 == 0:  # Every 100 cycles
                    self._cleanup_old_data()

                # Calculate sleep time
                elapsed = time.time() - start_time
                sleep_time = max(0.1, self.config.monitoring.check_interval - elapsed)

                if not self._stop_event.wait(sleep_time):
                    break

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                time.sleep(self.config.monitoring.check_interval)

        logger.info("Monitoring loop stopped")

    def _collect_resource_metrics(self) -> ResourceMetrics:
        """Collect current system resource metrics."""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=None)

            # Memory
            memory = psutil.virtual_memory()

            # Disk
            disk_percent = {}
            disk_used_gb = {}
            disk_free_gb = {}

            for partition in psutil.disk_partitions():
                if partition.fstype:  # Skip unmounted partitions
                    try:
                        usage = psutil.disk_usage(partition.mountpoint)
                        mount_point = partition.mountpoint
                        disk_percent[mount_point] = usage.percent
                        disk_used_gb[mount_point] = usage.used / (1024**3)  # GB
                        disk_free_gb[mount_point] = usage.free / (1024**3)  # GB
                    except (PermissionError, OSError):
                        continue

            # Network
            network = psutil.net_io_counters()
            bytes_sent = network.bytes_sent - self._last_network_counters.bytes_sent
            bytes_recv = network.bytes_recv - self._last_network_counters.bytes_recv
            self._last_network_counters = network

            # Process info
            process_count = len(psutil.pids())
            thread_count = sum(len(psutil.Process(pid).threads()) for pid in psutil.pids()[:10])  # Sample first 10

            return ResourceMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_mb=memory.used / (1024**2),
                memory_available_mb=memory.available / (1024**2),
                disk_percent=disk_percent,
                disk_used_gb=disk_used_gb,
                disk_free_gb=disk_free_gb,
                network_bytes_sent=bytes_sent,
                network_bytes_recv=bytes_recv,
                process_count=process_count,
                thread_count=thread_count
            )

        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
            # Return empty metrics on error
            return ResourceMetrics(
                timestamp=datetime.now(),
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_mb=0.0,
                memory_available_mb=0.0
            )

    def _check_scheduler_health(self) -> None:
        """Check scheduler health based on heartbeat."""
        time_since_heartbeat = (datetime.now() - self._last_scheduler_heartbeat).total_seconds()

        if time_since_heartbeat > self.config.alerting.scheduler_heartbeat_timeout:
            if self._scheduler_healthy:
                self._scheduler_healthy = False
                # Trigger alert
                self.alert_manager.process_event({
                    "type": "scheduler_down",
                    "last_heartbeat": self._last_scheduler_heartbeat.isoformat(),
                    "time_since_heartbeat": time_since_heartbeat
                })
                logger.warning(f"Scheduler heartbeat timeout: {time_since_heartbeat:.0f}s")

    def _check_resource_thresholds(self, metrics: ResourceMetrics) -> None:
        """Check resource metrics against thresholds."""
        # CPU threshold
        if metrics.cpu_percent > self.config.monitoring.cpu_threshold:
            self.alert_manager.process_event({
                "type": "cpu_high",
                "value": metrics.cpu_percent,
                "threshold": self.config.monitoring.cpu_threshold
            })

        # Memory threshold
        if metrics.memory_percent > self.config.monitoring.memory_threshold:
            self.alert_manager.process_event({
                "type": "memory_high",
                "value": metrics.memory_percent,
                "threshold": self.config.monitoring.memory_threshold
            })

        # Disk thresholds
        for mount_point, usage_percent in metrics.disk_percent.items():
            if usage_percent > self.config.monitoring.disk_threshold:
                self.alert_manager.process_event({
                    "type": "disk_high",
                    "mount_point": mount_point,
                    "value": usage_percent,
                    "threshold": self.config.monitoring.disk_threshold
                })

            free_gb = metrics.disk_free_gb.get(mount_point, 0)
            if free_gb < self.config.monitoring.disk_min_free_gb:
                self.alert_manager.process_event({
                    "type": "disk_low_free",
                    "mount_point": mount_point,
                    "value": free_gb,
                    "threshold": self.config.monitoring.disk_min_free_gb
                })

    def _check_job_alerts(self, job: JobMetrics) -> None:
        """Check job execution for alert conditions."""
        if not job.success:
            # Count recent failures for this job
            recent_failures = [
                j for j in self._job_history[-100:]  # Last 100 jobs
                if j.job_id == job.job_id and not j.success
            ]

            if len(recent_failures) >= self.config.alerting.job_failure_threshold:
                self.alert_manager.process_event({
                    "type": "job_failed",
                    "job_id": job.job_id,
                    "failure_count": len(recent_failures),
                    "last_error": job.error_message
                })

        # Check job timeout
        if job.duration and job.duration > self.config.alerting.job_timeout_threshold:
            self.alert_manager.process_event({
                "type": "job_timeout",
                "job_id": job.job_id,
                "duration": job.duration,
                "threshold": self.config.alerting.job_timeout_threshold
            })

    def _assess_health(self) -> SystemHealth:
        """Assess overall system health."""
        issues = []
        cpu_status = HealthStatus.HEALTHY.value
        memory_status = HealthStatus.HEALTHY.value
        disk_status = HealthStatus.HEALTHY.value
        scheduler_status = HealthStatus.HEALTHY.value

        # Get latest metrics
        if self._resource_history:
            latest = self._resource_history[-1]

            # CPU assessment
            if latest.cpu_percent > self.config.monitoring.cpu_threshold:
                cpu_status = HealthStatus.CRITICAL.value
                issues.append(f"High CPU usage: {latest.cpu_percent:.1f}%")
            elif latest.cpu_percent > self.config.monitoring.cpu_threshold * 0.8:
                cpu_status = HealthStatus.WARNING.value
                issues.append(f"Elevated CPU usage: {latest.cpu_percent:.1f}%")

            # Memory assessment
            if latest.memory_percent > self.config.monitoring.memory_threshold:
                memory_status = HealthStatus.CRITICAL.value
                issues.append(f"High memory usage: {latest.memory_percent:.1f}%")
            elif latest.memory_percent > self.config.monitoring.memory_threshold * 0.8:
                memory_status = HealthStatus.WARNING.value
                issues.append(f"Elevated memory usage: {latest.memory_percent:.1f}%")

            # Disk assessment
            critical_disks = []
            warning_disks = []
            for mount_point, usage in latest.disk_percent.items():
                free_gb = latest.disk_free_gb.get(mount_point, 0)
                if usage > self.config.monitoring.disk_threshold or free_gb < self.config.monitoring.disk_min_free_gb:
                    critical_disks.append(mount_point)
                elif usage > self.config.monitoring.disk_threshold * 0.9:
                    warning_disks.append(mount_point)

            if critical_disks:
                disk_status = HealthStatus.CRITICAL.value
                issues.extend([f"Critical disk usage: {mp}" for mp in critical_disks])
            elif warning_disks:
                disk_status = HealthStatus.WARNING.value
                issues.extend([f"High disk usage: {mp}" for mp in warning_disks])

        # Scheduler assessment
        time_since_heartbeat = (datetime.now() - self._last_scheduler_heartbeat).total_seconds()
        if time_since_heartbeat > self.config.alerting.scheduler_heartbeat_timeout:
            scheduler_status = HealthStatus.CRITICAL.value
            issues.append(f"Scheduler not responding ({time_since_heartbeat:.0f}s since heartbeat)")
        elif time_since_heartbeat > self.config.alerting.scheduler_heartbeat_timeout * 0.5:
            scheduler_status = HealthStatus.WARNING.value
            issues.append(f"Scheduler heartbeat delayed ({time_since_heartbeat:.0f}s)")

        # Overall assessment
        statuses = [cpu_status, memory_status, disk_status, scheduler_status]
        if HealthStatus.CRITICAL.value in statuses:
            overall_status = HealthStatus.CRITICAL.value
        elif HealthStatus.WARNING.value in statuses:
            overall_status = HealthStatus.WARNING.value
        else:
            overall_status = HealthStatus.HEALTHY.value

        return SystemHealth(
            overall_status=overall_status,
            cpu_status=cpu_status,
            memory_status=memory_status,
            disk_status=disk_status,
            scheduler_status=scheduler_status,
            last_check=datetime.now(),
            issues=issues
        )

    def _notify_health_callbacks(self, health: SystemHealth) -> None:
        """Notify health status change callbacks."""
        for callback in self._health_callbacks:
            try:
                callback(health)
            except Exception as e:
                logger.error(f"Health callback failed: {e}")

    def _handle_alert(self, alert) -> None:
        """Handle alerts from the alert manager."""
        # Log alert in monitoring context
        logger.info(f"Alert received: {alert.title} ({alert.severity.value})")

    def _cleanup_old_data(self) -> None:
        """Clean up old monitoring data."""
        cutoff_24h = datetime.now() - timedelta(hours=24)

        # Clean old resource history (keep last 24 hours)
        self._resource_history = [m for m in self._resource_history if m.timestamp >= cutoff_24h]

        # Clean old job history (keep last 7 days)
        cutoff_7d = datetime.now() - timedelta(days=7)
        with self._job_lock:
            self._job_history = [j for j in self._job_history if j.end_time and j.end_time >= cutoff_7d]


# Global instance
_monitoring_service = None

def get_monitoring_service() -> MonitoringService:
    """Get the global monitoring service instance."""
    global _monitoring_service
    if _monitoring_service is None:
        _monitoring_service = MonitoringService()
    return _monitoring_service


# Convenience functions
def start_system_monitoring() -> None:
    """Start the system monitoring service."""
    service = get_monitoring_service()
    service.start_monitoring()


def stop_system_monitoring() -> None:
    """Stop the system monitoring service."""
    service = get_monitoring_service()
    service.stop_monitoring()


def record_scheduler_heartbeat() -> None:
    """Record scheduler heartbeat."""
    service = get_monitoring_service()
    service.record_scheduler_heartbeat()


def start_job_monitoring(job_id: str, branch: str = "default") -> None:
    """Start monitoring a job execution."""
    service = get_monitoring_service()
    service.start_job_monitoring(job_id, branch)


def update_job_status(job_id: str, status: str, **kwargs) -> None:
    """Update job monitoring status."""
    service = get_monitoring_service()
    service.update_job_status(job_id, status, **kwargs)


def get_system_health() -> SystemHealth:
    """Get current system health assessment."""
    service = get_monitoring_service()
    return service.get_system_health()
    memory_used_mb: float = 0  # 0 means disabled
    disk_free_gb: float = 1.0  # Minimum free space in GB


class ResourceMonitor:
    """Production-grade resource monitoring system."""

    def __init__(self, config: Optional[Any] = None):
        """
        Initialize resource monitor.

        Args:
            config: Monitoring configuration
        """
        self.config = config or get_config().monitoring
        self.logger = get_monitoring_logger()

        # Monitoring state
        self._monitoring_active = False
        self._monitor_thread = None
        self._stop_event = threading.Event()

        # Metrics storage
        self._metrics_history: List[ResourceMetrics] = []
        self._max_history_size = 1000

        # Alert callbacks
        self._alert_callbacks: List[Callable[[str, Dict[str, Any]], None]] = []

        # Thresholds
        self.thresholds = AlertThresholds(
            cpu_percent=self.config.cpu_threshold,
            memory_percent=self.config.memory_threshold,
            disk_percent=self.config.disk_threshold,
            memory_used_mb=self.config.memory_max_mb,
            disk_free_gb=self.config.disk_min_free_gb
        )

        # Performance tracking
        self._last_network_counters = psutil.net_io_counters()

    def start_monitoring(self, interval: float = 30.0) -> None:
        """
        Start background resource monitoring.

        Args:
            interval: Monitoring interval in seconds
        """
        if self._monitoring_active:
            logger.warning("Resource monitoring already active")
            return

        self._monitoring_active = True
        self._stop_event.clear()

        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            name="resource-monitor",
            daemon=True
        )
        self._monitor_thread.start()

        logger.info(f"Resource monitoring started with {interval}s interval")

    def stop_monitoring(self) -> None:
        """Stop resource monitoring."""
        if not self._monitoring_active:
            return

        self._monitoring_active = False
        self._stop_event.set()

        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5.0)

        logger.info("Resource monitoring stopped")

    def add_alert_callback(self, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """
        Add a callback for resource alerts.

        Args:
            callback: Function to call on alerts (alert_type, alert_data)
        """
        self._alert_callbacks.append(callback)

    def get_current_metrics(self) -> ResourceMetrics:
        """
        Get current system resource metrics.

        Returns:
            Current resource metrics
        """
        return self._collect_metrics()

    def get_metrics_history(self, limit: Optional[int] = None) -> List[ResourceMetrics]:
        """
        Get historical metrics.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of historical metrics
        """
        if limit is None:
            return self._metrics_history.copy()
        return self._metrics_history[-limit:] if limit > 0 else []

    def get_average_metrics(self, minutes: int = 5) -> Optional[ResourceMetrics]:
        """
        Get average metrics over the last N minutes.

        Args:
            minutes: Number of minutes to average

        Returns:
            Averaged metrics or None if insufficient data
        """
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_metrics = [m for m in self._metrics_history if m.timestamp >= cutoff_time]

        if not recent_metrics:
            return None

        # Calculate averages
        avg_cpu = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_percent for m in recent_metrics) / len(recent_metrics)
        avg_memory_used = sum(m.memory_used_mb for m in recent_metrics) / len(recent_metrics)
        avg_memory_avail = sum(m.memory_available_mb for m in recent_metrics) / len(recent_metrics)

        # Average disk metrics
        disk_paths = set()
        for metric in recent_metrics:
            disk_paths.update(metric.disk_percent.keys())

        avg_disk_percent = {}
        avg_disk_used = {}
        avg_disk_free = {}

        for path in disk_paths:
            path_metrics = [m for m in recent_metrics if path in m.disk_percent]
            if path_metrics:
                avg_disk_percent[path] = sum(m.disk_percent[path] for m in path_metrics) / len(path_metrics)
                avg_disk_used[path] = sum(m.disk_used_gb[path] for m in path_metrics) / len(path_metrics)
                avg_disk_free[path] = sum(m.disk_free_gb[path] for m in path_metrics) / len(path_metrics)

        # Network totals (not averages)
        total_sent = sum(m.network_bytes_sent for m in recent_metrics)
        total_recv = sum(m.network_bytes_recv for m in recent_metrics)

        return ResourceMetrics(
            timestamp=datetime.now(),
            cpu_percent=avg_cpu,
            memory_percent=avg_memory,
            memory_used_mb=avg_memory_used,
            memory_available_mb=avg_memory_avail,
            disk_percent=avg_disk_percent,
            disk_used_gb=avg_disk_used,
            disk_free_gb=avg_disk_free,
            network_bytes_sent=total_sent,
            network_bytes_recv=total_recv,
            process_count=recent_metrics[-1].process_count if recent_metrics else 0,
            thread_count=recent_metrics[-1].thread_count if recent_metrics else 0
        )

    def check_health(self) -> Dict[str, Any]:
        """
        Perform comprehensive system health check.

        Returns:
            Health check results
        """
        health_status = {
            "overall": "healthy",
            "checks": {},
            "timestamp": datetime.now().isoformat()
        }

        try:
            # CPU health
            cpu_percent = psutil.cpu_percent(interval=1)
            health_status["checks"]["cpu"] = {
                "status": "healthy" if cpu_percent < self.thresholds.cpu_percent else "warning",
                "value": cpu_percent,
                "threshold": self.thresholds.cpu_percent
            }

            # Memory health
            memory = psutil.virtual_memory()
            memory_healthy = (memory.percent < self.thresholds.memory_percent and
                            (self.thresholds.memory_used_mb == 0 or
                             memory.used / (1024**2) < self.thresholds.memory_used_mb))
            health_status["checks"]["memory"] = {
                "status": "healthy" if memory_healthy else "critical",
                "used_percent": memory.percent,
                "used_mb": memory.used / (1024**2),
                "available_mb": memory.available / (1024**2),
                "threshold_percent": self.thresholds.memory_percent,
                "threshold_mb": self.thresholds.memory_used_mb
            }

            # Disk health
            disk_healthy = True
            disk_checks = {}
            for partition in psutil.disk_partitions():
                if partition.fstype:  # Skip unmounted partitions
                    try:
                        usage = psutil.disk_usage(partition.mountpoint)
                        usage_percent = usage.percent
                        free_gb = usage.free / (1024**3)

                        partition_healthy = (usage_percent < self.thresholds.disk_percent and
                                           free_gb > self.thresholds.disk_free_gb)

                        disk_checks[partition.mountpoint] = {
                            "status": "healthy" if partition_healthy else "critical",
                            "used_percent": usage_percent,
                            "free_gb": free_gb,
                            "threshold_percent": self.thresholds.disk_percent,
                            "threshold_free_gb": self.thresholds.disk_free_gb
                        }

                        if not partition_healthy:
                            disk_healthy = False

                    except (PermissionError, OSError):
                        disk_checks[partition.mountpoint] = {
                            "status": "unknown",
                            "error": "Permission denied or partition unavailable"
                        }

            health_status["checks"]["disk"] = {
                "status": "healthy" if disk_healthy else "critical",
                "partitions": disk_checks
            }

            # Overall status
            critical_checks = [check for check in health_status["checks"].values()
                             if isinstance(check, dict) and check.get("status") == "critical"]
            warning_checks = [check for check in health_status["checks"].values()
                            if isinstance(check, dict) and check.get("status") == "warning"]

            if critical_checks:
                health_status["overall"] = "critical"
            elif warning_checks:
                health_status["overall"] = "warning"

        except Exception as e:
            health_status["overall"] = "error"
            health_status["error"] = str(e)
            logger.error(f"Health check failed: {e}")

        return health_status

    def _monitor_loop(self, interval: float) -> None:
        """Main monitoring loop."""
        logger.info("Resource monitoring loop started")

        while not self._stop_event.is_set():
            try:
                start_time = time.time()

                # Collect metrics
                metrics = self._collect_metrics()

                # Store in history
                self._metrics_history.append(metrics)
                if len(self._metrics_history) > self._max_history_size:
                    self._metrics_history.pop(0)

                # Check thresholds and alert
                self._check_thresholds(metrics)

                # Calculate sleep time (adjust for collection time)
                elapsed = time.time() - start_time
                sleep_time = max(0.1, interval - elapsed)

                if not self._stop_event.wait(sleep_time):
                    break

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                time.sleep(interval)  # Wait before retrying

        logger.info("Resource monitoring loop stopped")

    def _collect_metrics(self) -> ResourceMetrics:
        """Collect current system resource metrics."""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=None)

            # Memory
            memory = psutil.virtual_memory()

            # Disk
            disk_percent = {}
            disk_used_gb = {}
            disk_free_gb = {}

            for partition in psutil.disk_partitions():
                if partition.fstype:  # Skip unmounted partitions
                    try:
                        usage = psutil.disk_usage(partition.mountpoint)
                        mount_point = partition.mountpoint
                        disk_percent[mount_point] = usage.percent
                        disk_used_gb[mount_point] = usage.used / (1024**3)  # GB
                        disk_free_gb[mount_point] = usage.free / (1024**3)  # GB
                    except (PermissionError, OSError):
                        continue

            # Network
            network = psutil.net_io_counters()
            bytes_sent = network.bytes_sent - self._last_network_counters.bytes_sent
            bytes_recv = network.bytes_recv - self._last_network_counters.bytes_recv
            self._last_network_counters = network

            # Process info
            process_count = len(psutil.pids())
            thread_count = sum(len(psutil.Process(pid).threads()) for pid in psutil.pids()[:10])  # Sample first 10

            return ResourceMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_mb=memory.used / (1024**2),
                memory_available_mb=memory.available / (1024**2),
                disk_percent=disk_percent,
                disk_used_gb=disk_used_gb,
                disk_free_gb=disk_free_gb,
                network_bytes_sent=bytes_sent,
                network_bytes_recv=bytes_recv,
                process_count=process_count,
                thread_count=thread_count
            )

        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
            # Return empty metrics on error
            return ResourceMetrics(
                timestamp=datetime.now(),
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_mb=0.0,
                memory_available_mb=0.0
            )

    def _check_thresholds(self, metrics: ResourceMetrics) -> None:
        """Check metrics against thresholds and trigger alerts."""
        alerts = []

        # CPU threshold
        if metrics.cpu_percent > self.thresholds.cpu_percent:
            alerts.append({
                "type": "cpu_high",
                "message": f"CPU usage is {metrics.cpu_percent:.1f}% (threshold: {self.thresholds.cpu_percent}%)",
                "value": metrics.cpu_percent,
                "threshold": self.thresholds.cpu_percent
            })

        # Memory thresholds
        if metrics.memory_percent > self.thresholds.memory_percent:
            alerts.append({
                "type": "memory_high_percent",
                "message": f"Memory usage is {metrics.memory_percent:.1f}% (threshold: {self.thresholds.memory_percent}%)",
                "value": metrics.memory_percent,
                "threshold": self.thresholds.memory_percent
            })

        if self.thresholds.memory_used_mb > 0 and metrics.memory_used_mb > self.thresholds.memory_used_mb:
            alerts.append({
                "type": "memory_high_used",
                "message": f"Memory used is {metrics.memory_used_mb:.1f}MB (threshold: {self.thresholds.memory_used_mb}MB)",
                "value": metrics.memory_used_mb,
                "threshold": self.thresholds.memory_used_mb
            })

        # Disk thresholds
        for mount_point, usage_percent in metrics.disk_percent.items():
            if usage_percent > self.thresholds.disk_percent:
                alerts.append({
                    "type": "disk_high_usage",
                    "message": f"Disk {mount_point} usage is {usage_percent:.1f}% (threshold: {self.thresholds.disk_percent}%)",
                    "mount_point": mount_point,
                    "value": usage_percent,
                    "threshold": self.thresholds.disk_percent
                })

            free_gb = metrics.disk_free_gb.get(mount_point, 0)
            if free_gb < self.thresholds.disk_free_gb:
                alerts.append({
                    "type": "disk_low_free",
                    "message": f"Disk {mount_point} free space is {free_gb:.1f}GB (minimum: {self.thresholds.disk_free_gb}GB)",
                    "mount_point": mount_point,
                    "value": free_gb,
                    "threshold": self.thresholds.disk_free_gb
                })

        # Trigger alerts
        for alert in alerts:
            alert_type = alert["type"]
            logger.warning(f"Resource alert: {alert['message']}", extra=alert)

            # Call alert callbacks
            for callback in self._alert_callbacks:
                try:
                    callback(alert_type, alert)
                except Exception as e:
                    logger.error(f"Alert callback failed: {e}")


# Global instance
_monitor = None

def get_resource_monitor() -> ResourceMonitor:
    """Get the global resource monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = ResourceMonitor()
    return _monitor


def start_resource_monitoring(interval: float = 30.0) -> None:
    """
    Start global resource monitoring.

    Args:
        interval: Monitoring interval in seconds
    """
    monitor = get_resource_monitor()
    monitor.start_monitoring(interval)


def stop_resource_monitoring() -> None:
    """Stop global resource monitoring."""
    monitor = get_resource_monitor()
    monitor.stop_monitoring()


def get_system_health() -> Dict[str, Any]:
    """
    Get current system health status.

    Returns:
        Health check results
    """
    monitor = get_resource_monitor()
    return monitor.check_health()