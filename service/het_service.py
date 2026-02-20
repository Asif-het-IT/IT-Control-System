#!/usr/bin/env python3
"""
HET IT Control System - Windows Service
Runs the scheduler as a Windows service without GUI
"""

import sys
import os
import time
import signal
import threading
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import servicemanager
    import win32serviceutil
    import win32service
    import win32event
    import win32api
    from app.config.settings import get_config
    from app.infrastructure.logger import setup_logging, get_scheduler_logger
    from app.infrastructure.scheduler import get_scheduler
    from app.infrastructure.database import get_db_manager
    from app.infrastructure.job_history_db import init_db as init_job_history_db
    from app.infrastructure.shutdown import get_shutdown_manager, register_shutdown_callback, ShutdownPhase
    from app.services.alert_manager import get_alert_manager
    from app.infrastructure.monitoring import get_monitoring_service
    from app.version import get_version_string
except ImportError as e:
    print(f"CRITICAL: Failed to import required modules: {e}")
    print("Please ensure all dependencies are installed.")
    sys.exit(1)


class HETService(win32serviceutil.ServiceFramework):
    """Windows service implementation for HET IT Control System."""

    _svc_name_ = "HETITControlSystem"
    _svc_display_name_ = "HET IT Control System"
    _svc_description_ = "Enterprise Automation Dashboard - Scheduler Service"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.logger = None
        self.scheduler = None
        self.monitoring = None
        self.alert_manager = None
        self.running = False

    def SvcStop(self):
        """Stop the service."""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.running = False

        if self.logger:
            self.logger.info("Service stop requested")

    def SvcDoRun(self):
        """Main service loop."""
        try:
            # Initialize service
            if not self.initialize_service():
                self.logger.error("Service initialization failed")
                return

            self.logger.info(f"HET IT Control System Service started - {get_version_string()}")
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, '')
            )

            self.running = True

            # Main service loop
            while self.running:
                # Check for stop event
                result = win32event.WaitForSingleObject(self.hWaitStop, 5000)  # 5 second timeout

                if result == win32event.WAIT_OBJECT_0:
                    # Stop event received
                    break

                # Service heartbeat
                self.perform_heartbeat()

            # Shutdown
            self.shutdown_service()

            self.logger.info("HET IT Control System Service stopped")
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STOPED,
                (self._svc_name_, '')
            )

        except Exception as e:
            if self.logger:
                self.logger.error(f"Service error: {e}", exc_info=True)
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_ERROR_TYPE,
                servicemanager.PYS_SERVICE_STOPED,
                (self._svc_name_, f'Error: {e}')
            )

    def initialize_service(self):
        """Initialize service components."""
        try:
            # Get configuration
            config = get_config()

            # Setup logging
            setup_logging(
                log_level=config.logging.level,
                log_dir=config.paths.logs_dir,
                max_bytes=config.logging.max_bytes,
                backup_count=config.logging.backup_count
            )

            self.logger = get_scheduler_logger()
            self.logger.info("Service initialization started")

            # Initialize database
            init_job_history_db()
            db_manager = get_db_manager()
            self.logger.info("Database initialized")

            # Initialize scheduler
            self.scheduler = get_scheduler()
            self.scheduler.start()
            self.logger.info("Scheduler started")

            # Initialize monitoring
            self.monitoring = get_monitoring_service()
            self.logger.info("Monitoring service initialized")

            # Initialize alert manager
            self.alert_manager = get_alert_manager()
            self.logger.info("Alert manager initialized")

            # Register shutdown callbacks
            shutdown_manager = get_shutdown_manager()
            register_shutdown_callback(
                self.shutdown_service,
                ShutdownPhase.SERVICES,
                "service_cleanup"
            )

            self.logger.info("Service initialization completed")
            return True

        except Exception as e:
            if self.logger:
                self.logger.error(f"Service initialization failed: {e}", exc_info=True)
            else:
                print(f"Service initialization failed: {e}")
            return False

    def perform_heartbeat(self):
        """Perform periodic service heartbeat."""
        try:
            # Update monitoring
            if self.monitoring:
                self.monitoring.record_heartbeat()

            # Check scheduler health
            if self.scheduler and hasattr(self.scheduler, 'get_jobs'):
                job_count = len(self.scheduler.get_jobs())
                self.logger.debug(f"Scheduler heartbeat: {job_count} jobs active")

        except Exception as e:
            if self.logger:
                self.logger.error(f"Heartbeat error: {e}")

    def shutdown_service(self):
        """Shutdown service components."""
        try:
            self.logger.info("Service shutdown started")

            # Stop scheduler
            if self.scheduler:
                self.scheduler.shutdown(wait=True)
                self.logger.info("Scheduler stopped")

            # Stop monitoring
            if self.monitoring:
                self.monitoring.stop()
                self.logger.info("Monitoring stopped")

            # Stop alert manager
            if self.alert_manager:
                self.alert_manager.stop()
                self.logger.info("Alert manager stopped")

            self.logger.info("Service shutdown completed")

        except Exception as e:
            if self.logger:
                self.logger.error(f"Service shutdown error: {e}")


def main():
    """Main entry point for Windows service."""
    if len(sys.argv) == 1:
        # Run as service
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(HETService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        # Handle command line arguments
        win32serviceutil.HandleCommandLine(HETService)


if __name__ == '__main__':
    main()