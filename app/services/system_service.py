# app/services/system_service.py
"""
System monitoring and operations service.
"""
import psutil
import platform
import subprocess
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

from app.config.settings import get_config
from app.infrastructure.logger import get_logger

logger = get_logger("system")


class SystemService:
    """Service for system monitoring and operations."""

    def __init__(self):
        self.config = get_config()

    def get_system_info(self) -> Dict[str, Any]:
        """
        Get basic system information.

        Returns:
            Dictionary with system information
        """
        try:
            return {
                'platform': platform.platform(),
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine(),
                'processor': platform.processor(),
                'python_version': platform.python_version(),
                'hostname': platform.node(),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get system info: {e}")
            return {}

    def get_cpu_info(self) -> Dict[str, Any]:
        """
        Get CPU information and usage.

        Returns:
            Dictionary with CPU information
        """
        try:
            return {
                'physical_cores': psutil.cpu_count(logical=False),
                'total_cores': psutil.cpu_count(logical=True),
                'cpu_percent': psutil.cpu_percent(interval=1, percpu=True),
                'cpu_freq': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
                'load_average': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
            }
        except Exception as e:
            logger.error(f"Failed to get CPU info: {e}")
            return {}

    def get_memory_info(self) -> Dict[str, Any]:
        """
        Get memory information and usage.

        Returns:
            Dictionary with memory information
        """
        try:
            mem = psutil.virtual_memory()
            return {
                'total': mem.total,
                'available': mem.available,
                'percent': mem.percent,
                'used': mem.used,
                'free': mem.free,
                'cached': getattr(mem, 'cached', 0),
                'buffers': getattr(mem, 'buffers', 0)
            }
        except Exception as e:
            logger.error(f"Failed to get memory info: {e}")
            return {}

    def get_disk_info(self) -> List[Dict[str, Any]]:
        """
        Get disk information and usage.

        Returns:
            List of dictionaries with disk information
        """
        try:
            disks = []
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disks.append({
                        'device': partition.device,
                        'mountpoint': partition.mountpoint,
                        'fstype': partition.fstype,
                        'opts': partition.opts,
                        'total': usage.total,
                        'used': usage.used,
                        'free': usage.free,
                        'percent': usage.percent
                    })
                except Exception as e:
                    logger.warning(f"Failed to get usage for {partition.mountpoint}: {e}")
                    continue
            return disks
        except Exception as e:
            logger.error(f"Failed to get disk info: {e}")
            return []

    def get_network_info(self) -> Dict[str, Any]:
        """
        Get network information and statistics.

        Returns:
            Dictionary with network information
        """
        try:
            net_io = psutil.net_io_counters()
            return {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv,
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv,
                'errin': net_io.errin,
                'errout': net_io.errout,
                'dropin': net_io.dropin,
                'dropout': net_io.dropout
            }
        except Exception as e:
            logger.error(f"Failed to get network info: {e}")
            return {}

    def get_process_info(self, pid: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Get process information.

        Args:
            pid: Process ID (current process if None)

        Returns:
            Dictionary with process information, or None if error
        """
        try:
            if pid is None:
                process = psutil.Process()
            else:
                process = psutil.Process(pid)

            return {
                'pid': process.pid,
                'name': process.name(),
                'status': process.status(),
                'cpu_percent': process.cpu_percent(),
                'memory_percent': process.memory_percent(),
                'memory_info': process.memory_info()._asdict(),
                'num_threads': process.num_threads(),
                'create_time': process.create_time()
            }
        except Exception as e:
            logger.error(f"Failed to get process info for PID {pid}: {e}")
            return None

    def run_system_command(
        self,
        command: str,
        timeout: int = 30,
        shell: bool = False
    ) -> Dict[str, Any]:
        """
        Run a system command.

        Args:
            command: Command to run
            timeout: Command timeout in seconds
            shell: Whether to run in shell

        Returns:
            Dictionary with command results
        """
        try:
            result = subprocess.run(
                command,
                shell=shell,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            return {
                'success': result.returncode == 0,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'command': command
            }

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'returncode': -1,
                'stdout': '',
                'stderr': f'Command timed out after {timeout} seconds',
                'command': command
            }
        except Exception as e:
            return {
                'success': False,
                'returncode': -1,
                'stdout': '',
                'stderr': str(e),
                'command': command
            }

    def get_service_status(self, service_name: str) -> Optional[Dict[str, Any]]:
        """
        Get Windows service status.

        Args:
            service_name: Name of the service

        Returns:
            Dictionary with service information, or None if not found
        """
        try:
            import win32serviceutil
            import win32service

            status = win32serviceutil.QueryServiceStatus(service_name)

            status_text = {
                win32service.SERVICE_STOPPED: "stopped",
                win32service.SERVICE_START_PENDING: "start_pending",
                win32service.SERVICE_STOP_PENDING: "stop_pending",
                win32service.SERVICE_RUNNING: "running",
                win32service.SERVICE_CONTINUE_PENDING: "continue_pending",
                win32service.SERVICE_PAUSE_PENDING: "pause_pending",
                win32service.SERVICE_PAUSED: "paused"
            }.get(status[1], "unknown")

            return {
                'name': service_name,
                'status': status_text,
                'status_code': status[1],
                'controls_accepted': status[2]
            }

        except Exception as e:
            logger.error(f"Failed to get service status for {service_name}: {e}")
            return None

    def start_service(self, service_name: str) -> bool:
        """
        Start a Windows service.

        Args:
            service_name: Name of the service

        Returns:
            True if started successfully, False otherwise
        """
        try:
            import win32serviceutil
            win32serviceutil.StartService(service_name)
            logger.info(f"Service started: {service_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to start service {service_name}: {e}")
            return False

    def stop_service(self, service_name: str) -> bool:
        """
        Stop a Windows service.

        Args:
            service_name: Name of the service

        Returns:
            True if stopped successfully, False otherwise
        """
        try:
            import win32serviceutil
            win32serviceutil.StopService(service_name)
            logger.info(f"Service stopped: {service_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to stop service {service_name}: {e}")
            return False

    def get_system_health(self) -> Dict[str, Any]:
        """
        Get overall system health metrics.

        Returns:
            Dictionary with health metrics
        """
        try:
            cpu = self.get_cpu_info()
            memory = self.get_memory_info()
            disk = self.get_disk_info()

            # Calculate health scores
            cpu_health = 100 - (sum(cpu.get('cpu_percent', [0])) / len(cpu.get('cpu_percent', [1])))
            memory_health = 100 - memory.get('percent', 0)

            disk_health = 100
            if disk:
                total_disk_percent = sum(d.get('percent', 0) for d in disk) / len(disk)
                disk_health = 100 - total_disk_percent

            overall_health = (cpu_health + memory_health + disk_health) / 3

            return {
                'overall_health': round(overall_health, 2),
                'cpu_health': round(cpu_health, 2),
                'memory_health': round(memory_health, 2),
                'disk_health': round(disk_health, 2),
                'timestamp': datetime.now().isoformat(),
                'details': {
                    'cpu': cpu,
                    'memory': memory,
                    'disk': disk
                }
            }

        except Exception as e:
            logger.error(f"Failed to get system health: {e}")
            return {
                'overall_health': 0,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }


# Global system service instance
_system_service = None

def get_system_service() -> SystemService:
    """Get the global system service instance."""
    global _system_service
    if _system_service is None:
        _system_service = SystemService()
    return _system_service