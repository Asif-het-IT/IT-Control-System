# app/services/network_service.py
"""
Network operations service for SMB, remote file access, etc.
"""
import os
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import logging
import subprocess

from app.config.settings import get_config
from app.infrastructure.logger import get_logger
from app.infrastructure.exceptions import NetworkError

logger = get_logger("network")


class NetworkService:
    """Service for network operations."""

    def __init__(self):
        self.config = get_config()

    def check_network_path(self, path: Path) -> bool:
        """
        Check if a network path is accessible.

        Args:
            path: Network path to check

        Returns:
            True if accessible, False otherwise
        """
        try:
            # Try to list directory contents
            list(path.iterdir())[:1]  # Just check if we can iterate
            return True
        except Exception as e:
            logger.warning(f"Network path not accessible: {path} - {e}")
            return False

    def mount_network_drive(
        self,
        remote_path: str,
        local_drive: str,
        username: Optional[str] = None,
        password: Optional[str] = None
    ) -> bool:
        """
        Mount a network drive (Windows only).

        Args:
            remote_path: Remote network path
            local_drive: Local drive letter (e.g., 'Z:')
            username: Username for authentication
            password: Password for authentication

        Returns:
            True if mounted successfully, False otherwise
        """
        try:
            import subprocess

            cmd = ['net', 'use', local_drive, remote_path]
            if username:
                cmd.extend(['/user:' + username])
                if password:
                    cmd.append(password)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                logger.info(f"Network drive mounted: {local_drive} -> {remote_path}")
                return True
            else:
                logger.error(f"Failed to mount network drive: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error mounting network drive: {e}")
            return False

    def unmount_network_drive(self, local_drive: str) -> bool:
        """
        Unmount a network drive.

        Args:
            local_drive: Local drive letter to unmount

        Returns:
            True if unmounted successfully, False otherwise
        """
        try:
            import subprocess

            result = subprocess.run(
                ['net', 'use', local_drive, '/delete'],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                logger.info(f"Network drive unmounted: {local_drive}")
                return True
            else:
                logger.error(f"Failed to unmount network drive: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error unmounting network drive: {e}")
            return False

    def list_network_directory(self, path: Path) -> List[Dict[str, Any]]:
        """
        List contents of a network directory.

        Args:
            path: Network directory path

        Returns:
            List of file/directory information dictionaries
        """
        try:
            items = []
            for item in path.iterdir():
                try:
                    stat = item.stat()
                    items.append({
                        'name': item.name,
                        'path': str(item),
                        'is_file': item.is_file(),
                        'is_dir': item.is_dir(),
                        'size': stat.st_size if item.is_file() else 0,
                        'modified': stat.st_mtime,
                        'created': stat.st_ctime
                    })
                except Exception as e:
                    logger.warning(f"Failed to get info for {item}: {e}")
                    continue

            return items

        except Exception as e:
            logger.error(f"Failed to list network directory {path}: {e}")
            return []

    def copy_from_network(
        self,
        remote_path: Path,
        local_path: Path,
        overwrite: bool = False
    ) -> bool:
        """
        Copy file from network to local.

        Args:
            remote_path: Remote file path
            local_path: Local destination path
            overwrite: Whether to overwrite existing file

        Returns:
            True if copied successfully, False otherwise
        """
        try:
            if local_path.exists() and not overwrite:
                logger.warning(f"Local file exists, skipping: {local_path}")
                return False

            local_path.parent.mkdir(parents=True, exist_ok=True)

            # Use shutil for network copy
            import shutil
            shutil.copy2(str(remote_path), str(local_path))

            logger.info(f"File copied from network: {remote_path} -> {local_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to copy from network {remote_path} to {local_path}: {e}")
            return False

    def copy_to_network(
        self,
        local_path: Path,
        remote_path: Path,
        overwrite: bool = False
    ) -> bool:
        """
        Copy file from local to network.

        Args:
            local_path: Local file path
            remote_path: Remote destination path
            overwrite: Whether to overwrite existing file

        Returns:
            True if copied successfully, False otherwise
        """
        try:
            if remote_path.exists() and not overwrite:
                logger.warning(f"Remote file exists, skipping: {remote_path}")
                return False

            remote_path.parent.mkdir(parents=True, exist_ok=True)

            # Use shutil for network copy
            import shutil
            shutil.copy2(str(local_path), str(remote_path))

            logger.info(f"File copied to network: {local_path} -> {remote_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to copy to network {local_path} to {remote_path}: {e}")
            return False

    def test_network_connectivity(self, host: str, timeout: int = 5) -> Tuple[bool, Optional[str]]:
        """
        Test network connectivity to a host.

        Args:
            host: Host to test connectivity to
            timeout: Timeout in seconds

        Returns:
            Tuple of (is_connected, error_message)
        """
        try:
            import socket
            socket.setdefaulttimeout(timeout)

            # Try to resolve hostname
            socket.gethostbyname(host)

            # Try to connect to common ports
            test_ports = [445, 139, 80, 443]  # SMB, NetBIOS, HTTP, HTTPS
            connected = False

            for port in test_ports:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.connect((host, port))
                    sock.close()
                    connected = True
                    break
                except:
                    continue

            if connected:
                return True, None
            else:
                return False, "Host reachable but no services responding"

        except socket.gaierror:
            return False, "DNS resolution failed"
        except Exception as e:
            return False, str(e)

    def get_network_drives(self) -> Dict[str, str]:
        """
        Get list of mounted network drives (Windows only).

        Returns:
            Dictionary mapping drive letters to network paths
        """
        try:
            import subprocess

            result = subprocess.run(
                ['net', 'use'],
                capture_output=True,
                text=True,
                timeout=30
            )

            drives = {}
            lines = result.stdout.split('\n')

            for line in lines:
                if line.strip() and not line.startswith('---') and not line.startswith('The command completed'):
                    parts = line.split()
                    if len(parts) >= 3 and parts[0].endswith(':') and parts[2].startswith('\\\\'):
                        drives[parts[0]] = parts[2]

            return drives

        except Exception as e:
            logger.error(f"Failed to get network drives: {e}")
            return {}


# Global network service instance
_network_service = None

def get_network_service() -> NetworkService:
    """Get the global network service instance."""
    global _network_service
    if _network_service is None:
        _network_service = NetworkService()
    return _network_service