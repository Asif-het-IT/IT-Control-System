# scripts/service_manager.py
"""
Service management utilities for HET IT Control System.
Provides install, uninstall, start, stop, and status commands.
"""

import win32serviceutil
import win32service
import win32api
import win32con
import sys
import os
from pathlib import Path
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.infrastructure.logging import init_logging, get_service_logger

logger = get_service_logger()

SERVICE_NAME = "HET-IT-Control-System"
SERVICE_DISPLAY_NAME = "HET IT Control System"
SERVICE_DESCRIPTION = "Automated IT control and monitoring service"

class ServiceManager:
    """Manages Windows service operations."""

    def __init__(self):
        self.service_name = SERVICE_NAME

    def install(self):
        """Install the Windows service."""
        try:
            # Get the service executable path
            exe_path = self._get_service_exe_path()

            # Install service
            win32serviceutil.InstallService(
                None,  # service class
                self.service_name,
                SERVICE_DISPLAY_NAME,
                exe_path,
                startType=win32service.SERVICE_AUTO_START,
                description=SERVICE_DESCRIPTION
            )

            logger.info(f"Service '{self.service_name}' installed successfully")
            print(f"Service '{SERVICE_DISPLAY_NAME}' installed successfully")
            print("Service will start automatically on system boot")

        except Exception as e:
            logger.error(f"Failed to install service: {e}")
            print(f"Failed to install service: {e}")
            return False

        return True

    def uninstall(self):
        """Uninstall the Windows service."""
        try:
            # Stop service if running
            if self.is_running():
                self.stop()

            # Remove service
            win32serviceutil.RemoveService(self.service_name)

            logger.info(f"Service '{self.service_name}' uninstalled successfully")
            print(f"Service '{SERVICE_DISPLAY_NAME}' uninstalled successfully")

        except Exception as e:
            logger.error(f"Failed to uninstall service: {e}")
            print(f"Failed to uninstall service: {e}")
            return False

        return True

    def start(self):
        """Start the Windows service."""
        try:
            win32serviceutil.StartService(self.service_name)
            logger.info(f"Service '{self.service_name}' started")
            print(f"Service '{SERVICE_DISPLAY_NAME}' started")

        except Exception as e:
            logger.error(f"Failed to start service: {e}")
            print(f"Failed to start service: {e}")
            return False

        return True

    def stop(self):
        """Stop the Windows service."""
        try:
            win32serviceutil.StopService(self.service_name)
            logger.info(f"Service '{self.service_name}' stopped")
            print(f"Service '{SERVICE_DISPLAY_NAME}' stopped")

        except Exception as e:
            logger.error(f"Failed to stop service: {e}")
            print(f"Failed to stop service: {e}")
            return False

        return True

    def restart(self):
        """Restart the Windows service."""
        if not self.stop():
            return False
        return self.start()

    def status(self):
        """Get service status."""
        try:
            status = win32serviceutil.QueryServiceStatus(self.service_name)

            status_map = {
                win32service.SERVICE_STOPPED: "STOPPED",
                win32service.SERVICE_START_PENDING: "STARTING",
                win32service.SERVICE_STOP_PENDING: "STOPPING",
                win32service.SERVICE_RUNNING: "RUNNING",
                win32service.SERVICE_CONTINUE_PENDING: "CONTINUING",
                win32service.SERVICE_PAUSE_PENDING: "PAUSING",
                win32service.SERVICE_PAUSED: "PAUSED",
            }

            status_str = status_map.get(status[1], f"UNKNOWN ({status[1]})")

            print(f"Service: {SERVICE_DISPLAY_NAME}")
            print(f"Status: {status_str}")

            if status[1] == win32service.SERVICE_RUNNING:
                print("The service is running and monitoring jobs")
            elif status[1] == win32service.SERVICE_STOPPED:
                print("The service is stopped")

            return status[1]

        except Exception as e:
            logger.error(f"Failed to get service status: {e}")
            print(f"Failed to get service status: {e}")
            print("Service may not be installed")
            return None

    def is_running(self):
        """Check if service is running."""
        status = self.status()
        return status == win32service.SERVICE_RUNNING

    def is_installed(self):
        """Check if service is installed."""
        try:
            win32serviceutil.QueryServiceStatus(self.service_name)
            return True
        except:
            return False

    def _get_service_exe_path(self):
        """Get the path to the service executable."""
        # For development, use the Python script
        # For production, this should be the PyInstaller EXE
        script_dir = Path(__file__).parent
        service_script = script_dir / ".." / "app" / "service" / "windows_service.py"

        # Use pythonw.exe to run without console window
        python_exe = sys.executable.replace("python.exe", "pythonw.exe")

        return f'"{python_exe}" "{service_script}"'


def main():
    """Command line interface for service management."""
    init_logging("service", "INFO")

    if len(sys.argv) < 2:
        print("Usage: python service_manager.py <command>")
        print("Commands: install, uninstall, start, stop, restart, status")
        return

    command = sys.argv[1].lower()
    manager = ServiceManager()

    if command == "install":
        manager.install()
    elif command == "uninstall":
        manager.uninstall()
    elif command == "start":
        manager.start()
    elif command == "stop":
        manager.stop()
    elif command == "restart":
        manager.restart()
    elif command == "status":
        manager.status()
    else:
        print(f"Unknown command: {command}")
        print("Available commands: install, uninstall, start, stop, restart, status")


if __name__ == '__main__':
    main()
<parameter name="filePath">d:\My App\scripts\service_manager.py