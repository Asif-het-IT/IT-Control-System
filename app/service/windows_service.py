# app/service/windows_service.py
"""
Windows Service implementation for HET IT Control System.
Runs jobs in background even when no user is logged in.
"""

import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import time
import sys
import logging
import threading
from typing import Optional

from app.infrastructure.logging import init_logging, get_service_logger
from app.infrastructure.scheduler import get_scheduler
from app.infrastructure.database import get_database_manager

logger = get_service_logger()

class HETService(win32serviceutil.ServiceFramework):
    """Windows Service for het IT Control System."""

    _svc_name_ = "het-service"
    _svc_display_name_ = "het IT Control System"
    _svc_description_ = "Automated IT control and monitoring service"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.is_running = False

        # Components
        self.scheduler = None
        self.db_manager = None
        self.heartbeat_count = 0

    def SvcStop(self):
        """Stop the service."""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        logger.info("Service stop requested")

        win32event.SetEvent(self.hWaitStop)
        self.is_running = False

        # Clean shutdown
        self._shutdown_components()

    def SvcDoRun(self):
        """Main service execution loop."""
        try:
            # Report service as starting
            self.ReportServiceStatus(win32service.SERVICE_START_PENDING)
            logger.info("HET Service starting...")

            # Start worker thread for main operations
            self.worker_thread = threading.Thread(target=self.main_loop)
            self.worker_thread.daemon = True
            self.worker_thread.start()

            # Report service as running
            self.ReportServiceStatus(win32service.SERVICE_RUNNING)
            logger.info("HET Service reported as running")

            # Wait for stop signal
            win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)

            # Wait for worker thread to finish
            if self.worker_thread.is_alive():
                self.worker_thread.join(timeout=30)

            # Report service as stopped
            self.ReportServiceStatus(win32service.SERVICE_STOPPED)
            logger.info("HET Service stopped")

        except Exception as e:
            logger.error(f"Service error: {e}")
            servicemanager.LogErrorMsg(f"Service error: {e}")
            self.ReportServiceStatus(win32service.SERVICE_STOPPED)
            raise

    def main_loop(self):
        """Main service loop running in worker thread."""
        try:
            # Initialize components (heavy operations)
            self._initialize_components()

            # Report service started via event log
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, '')
            )

            self.is_running = True
            logger.info("HET Service started successfully")

            # Main service loop
            while self.is_running:
                try:
                    # Check for stop signal
                    result = win32event.WaitForSingleObject(self.hWaitStop, 30000)  # 30 seconds

                    if result == win32event.WAIT_OBJECT_0:
                        break

                    # Perform periodic tasks
                    self._perform_heartbeat()

                except KeyboardInterrupt:
                    # Handle Ctrl+C in debug mode
                    logger.info("Service interrupted")
                    break

        except Exception as e:
            logger.error(f"Service main loop error: {e}")
            servicemanager.LogErrorMsg(f"Service main loop error: {e}")
            self.is_running = False
        finally:
            self._shutdown_components()

    def _initialize_components(self):
        """Initialize service components."""
        try:
            # Initialize database
            self.db_manager = get_database_manager()
            logger.info("Database manager initialized")

            # Initialize scheduler
            self.scheduler = get_scheduler()
            self.scheduler.initialize()
            self.scheduler.start()
            logger.info("Scheduler initialized and started")

            # TODO: Load and schedule jobs from database
            self._load_scheduled_jobs()

            logger.info("All service components initialized")

        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise

    def _shutdown_components(self):
        """Shutdown service components gracefully."""
        try:
            if self.scheduler:
                self.scheduler.stop()
                logger.info("Scheduler stopped")

            logger.info("Service components shut down")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    def _load_scheduled_jobs(self):
        """Load and schedule jobs from database."""
        # TODO: Implement job loading from database
        # For now, add a simple heartbeat job
        try:
            self.scheduler.add_job(
                "service_heartbeat",
                self._service_heartbeat_job,
                trigger="interval",
                minutes=5
            )
            logger.info("Heartbeat job scheduled")
        except Exception as e:
            logger.error(f"Failed to schedule heartbeat job: {e}")

    def _perform_heartbeat(self):
        """Perform periodic service health check."""
        self.heartbeat_count += 1

        try:
            # Check scheduler health
            if self.scheduler and self.scheduler.is_running():
                logger.debug(f"Service heartbeat #{self.heartbeat_count} - Scheduler OK")
            else:
                logger.warning("Service heartbeat - Scheduler not running")

            # Check database health
            if self.db_manager:
                db_size = self.db_manager.get_db_size()
                logger.debug(f"Database size: {db_size} bytes")

            # Create daily backup if needed
            self._check_daily_backup()

        except Exception as e:
            logger.error(f"Heartbeat error: {e}")

    def _service_heartbeat_job(self):
        """Scheduled heartbeat job."""
        logger.info("Service heartbeat job executed")

    def _check_daily_backup(self):
        """Check if daily database backup is needed."""
        # TODO: Implement daily backup logic
        pass


def main():
    """Service entry point."""
    if len(sys.argv) == 1:
        # No arguments - show help message
        print("het IT Control System Service")
        print("Usage:")
        print("  het_service.exe install   - Install the service")
        print("  het_service.exe start     - Start the service")
        print("  het_service.exe stop      - Stop the service")
        print("  het_service.exe remove    - Remove the service")
        print("  het_service.exe status    - Show service status")
        print("  het_service.exe debug     - Run in console debug mode")
        return
    elif len(sys.argv) == 2 and sys.argv[1] == "debug":
        # Debug mode - run in console
        print("Running het service in debug mode...")
        init_logging("service", "INFO")

        # Create a minimal service instance for debug mode
        class DebugService:
            def __init__(self):
                self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
                self.is_running = False
                self.scheduler = None
                self.db_manager = None
                self.heartbeat_count = 0

            def _initialize_components(self):
                """Initialize service components."""
                try:
                    # Initialize database
                    self.db_manager = get_database_manager()
                    logger.info("Database manager initialized")

                    # Initialize scheduler
                    self.scheduler = get_scheduler()
                    self.scheduler.initialize()
                    self.scheduler.start()
                    logger.info("Scheduler initialized and started")

                    # TODO: Load and schedule jobs from database
                    self._load_scheduled_jobs()

                    logger.info("All service components initialized")

                except Exception as e:
                    logger.error(f"Failed to initialize components: {e}")
                    raise

            def _shutdown_components(self):
                """Shutdown service components gracefully."""
                try:
                    if self.scheduler:
                        self.scheduler.stop()
                        logger.info("Scheduler stopped")

                    logger.info("Service components shut down")

                except Exception as e:
                    logger.error(f"Error during shutdown: {e}")

            def _load_scheduled_jobs(self):
                """Load and schedule jobs from database."""
                # TODO: Implement job loading from database
                # For now, add a simple heartbeat job
                try:
                    self.scheduler.add_job(
                        "service_heartbeat",
                        self._service_heartbeat_job,
                        trigger="interval",
                        minutes=5
                    )
                    logger.info("Heartbeat job scheduled")
                except Exception as e:
                    logger.error(f"Failed to schedule heartbeat job: {e}")

            def _perform_heartbeat(self):
                """Perform periodic service health check."""
                self.heartbeat_count += 1

                try:
                    # Check scheduler health
                    if self.scheduler and self.scheduler.is_running():
                        logger.debug(f"Service heartbeat #{self.heartbeat_count} - Scheduler OK")
                    else:
                        logger.warning("Service heartbeat - Scheduler not running")

                    # Check database health
                    if self.db_manager:
                        db_size = self.db_manager.get_db_size()
                        logger.debug(f"Database size: {db_size} bytes")

                    # Create daily backup if needed
                    self._check_daily_backup()

                except Exception as e:
                    logger.error(f"Heartbeat error: {e}")

            def _service_heartbeat_job(self):
                """Scheduled heartbeat job."""
                logger.info("Service heartbeat job executed")

            def _check_daily_backup(self):
                """Check if daily database backup is needed."""
                # TODO: Implement daily backup logic
                pass

            def main_loop(self):
                """Main service loop for debug mode."""
                try:
                    # Initialize components (heavy operations)
                    self._initialize_components()

                    self.is_running = True
                    logger.info("het service started in debug mode")
                    print("Service running in debug mode. Press Ctrl+C to stop.")

                    # Main service loop
                    while self.is_running:
                        try:
                            # Check for stop signal (though in debug mode we mainly wait for interrupt)
                            result = win32event.WaitForSingleObject(self.hWaitStop, 30000)  # 30 seconds

                            if result == win32event.WAIT_OBJECT_0:
                                break

                            # Perform periodic tasks
                            self._perform_heartbeat()

                        except KeyboardInterrupt:
                            # Handle Ctrl+C in debug mode
                            logger.info("Service interrupted")
                            break

                except Exception as e:
                    logger.error(f"Service main loop error: {e}")
                    print(f"Error in debug mode: {e}")
                finally:
                    self._shutdown_components()

        service = DebugService()
        try:
            # Run main loop directly in debug mode
            service.main_loop()
        except KeyboardInterrupt:
            logger.info("Debug mode stopped by user")
            print("Debug mode stopped.")
        # Note: main_loop() handles shutdown in finally block
    else:
        # Handle service commands (install/start/stop/remove/status)
        win32serviceutil.HandleCommandLine(HETService)


if __name__ == '__main__':
    main()