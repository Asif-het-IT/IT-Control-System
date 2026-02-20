#!/usr/bin/env python3
"""
HET IT Control System - Auto Update System
Handles version checking and application updates
"""

import sys
import os
import json
import hashlib
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from urllib.request import urlopen, Request
from urllib.error import URLError

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from app.config.settings import get_config
    from app.infrastructure.logger import get_scheduler_logger
    from app.version import __version__, get_version_info
    from app.infrastructure.exceptions import ConfigurationError

except ImportError as e:
    print(f"CRITICAL: Failed to import required modules: {e}")
    sys.exit(1)


class UpdateManager:
    """Manages application updates."""

    def __init__(self):
        self.config = get_config()
        self.logger = get_scheduler_logger()
        self.update_url = self.config.updates.update_url if hasattr(self.config, 'updates') else None
        self.current_version = __version__

    def check_for_updates(self) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Check for available updates.

        Returns:
            Tuple of (update_available, latest_version, update_info)
        """
        if not self.update_url:
            self.logger.debug("Update URL not configured")
            return False, None, None

        try:
            self.logger.info("Checking for updates...")

            # Create request with user agent
            req = Request(
                self.update_url,
                headers={
                    'User-Agent': f'HET-IT-Control-System/{self.current_version}',
                    'Accept': 'application/json'
                }
            )

            # Fetch update information
            with urlopen(req, timeout=30) as response:
                update_data = json.loads(response.read().decode('utf-8'))

            latest_version = update_data.get('version')
            if not latest_version:
                self.logger.warning("No version information in update response")
                return False, None, None

            # Compare versions
            if self._is_newer_version(latest_version, self.current_version):
                self.logger.info(f"Update available: {latest_version} (current: {self.current_version})")
                return True, latest_version, update_data
            else:
                self.logger.info(f"Application is up to date (version {self.current_version})")
                return False, latest_version, update_data

        except URLError as e:
            self.logger.error(f"Failed to check for updates: {e}")
            return False, None, None
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid update response: {e}")
            return False, None, None
        except Exception as e:
            self.logger.error(f"Unexpected error checking for updates: {e}")
            return False, None, None

    def download_update(self, update_info: Dict[str, Any]) -> Optional[Path]:
        """
        Download update package.

        Args:
            update_info: Update information from server

        Returns:
            Path to downloaded update file, or None if failed
        """
        download_url = update_info.get('download_url')
        if not download_url:
            self.logger.error("No download URL in update information")
            return None

        expected_hash = update_info.get('sha256_hash')

        try:
            self.logger.info(f"Downloading update from {download_url}")

            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_file:
                temp_path = Path(temp_file.name)

            # Download file
            req = Request(
                download_url,
                headers={
                    'User-Agent': f'HET-IT-Control-System/{self.current_version}'
                }
            )

            with urlopen(req, timeout=300) as response:  # 5 minute timeout
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0

                with open(temp_path, 'wb') as f:
                    while True:
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)

                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            self.logger.debug(f"Download progress: {progress:.1f}%")

            # Verify hash if provided
            if expected_hash:
                actual_hash = self._calculate_file_hash(temp_path)
                if actual_hash != expected_hash:
                    self.logger.error(f"Hash verification failed. Expected: {expected_hash}, Got: {actual_hash}")
                    temp_path.unlink()
                    return None
                self.logger.info("Update file hash verified")

            self.logger.info(f"Update downloaded successfully: {temp_path}")
            return temp_path

        except Exception as e:
            self.logger.error(f"Failed to download update: {e}")
            if temp_path.exists():
                temp_path.unlink()
            return None

    def apply_update(self, update_file: Path) -> bool:
        """
        Apply downloaded update.

        Args:
            update_file: Path to update file

        Returns:
            True if update applied successfully
        """
        try:
            self.logger.info("Applying update...")

            # Create backup of current installation
            backup_dir = self._create_backup()
            if not backup_dir:
                self.logger.error("Failed to create backup")
                return False

            # Extract update
            import zipfile
            extract_dir = PROJECT_ROOT / "update_temp"
            extract_dir.mkdir(exist_ok=True)

            with zipfile.ZipFile(update_file, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            # Validate update structure
            if not self._validate_update_structure(extract_dir):
                self.logger.error("Invalid update structure")
                extract_dir.rmdir()
                return False

            # Apply update
            if not self._apply_update_files(extract_dir):
                self.logger.error("Failed to apply update files")
                self._restore_backup(backup_dir)
                extract_dir.rmdir()
                return False

            # Update version
            self._update_version_info(extract_dir)

            # Cleanup
            extract_dir.rmdir()
            update_file.unlink()

            self.logger.info("Update applied successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to apply update: {e}")
            return False

    def _is_newer_version(self, version1: str, version2: str) -> bool:
        """Check if version1 is newer than version2."""
        def parse_version(v: str) -> Tuple[int, ...]:
            return tuple(int(x) for x in v.split('.') if x.isdigit())

        try:
            v1_parts = parse_version(version1)
            v2_parts = parse_version(version2)

            # Pad shorter version with zeros
            max_len = max(len(v1_parts), len(v2_parts))
            v1_parts = v1_parts + (0,) * (max_len - len(v1_parts))
            v2_parts = v2_parts + (0,) * (max_len - len(v2_parts))

            return v1_parts > v2_parts
        except:
            return False

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file."""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def _create_backup(self) -> Optional[Path]:
        """Create backup of current installation."""
        try:
            backup_dir = PROJECT_ROOT / f"backup_{self.current_version}"
            backup_dir.mkdir(exist_ok=True)

            # Backup important files
            important_files = [
                "app/",
                "requirements.txt",
                "run.py",
                "app/version.py"
            ]

            for file_pattern in important_files:
                src = PROJECT_ROOT / file_pattern
                if src.exists():
                    if src.is_file():
                        import shutil
                        shutil.copy2(src, backup_dir / src.name)
                    else:
                        import shutil
                        shutil.copytree(src, backup_dir / src.name, dirs_exist_ok=True)

            self.logger.info(f"Backup created: {backup_dir}")
            return backup_dir

        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            return None

    def _validate_update_structure(self, update_dir: Path) -> bool:
        """Validate update package structure."""
        required_files = [
            "app/version.py",
            "run.py"
        ]

        for file_path in required_files:
            if not (update_dir / file_path).exists():
                self.logger.error(f"Required file missing in update: {file_path}")
                return False

        return True

    def _apply_update_files(self, update_dir: Path) -> bool:
        """Apply update files to installation."""
        try:
            import shutil

            # Copy all files from update directory
            for item in update_dir.rglob('*'):
                if item.is_file():
                    relative_path = item.relative_to(update_dir)
                    dest_path = PROJECT_ROOT / relative_path

                    # Create parent directories
                    dest_path.parent.mkdir(parents=True, exist_ok=True)

                    # Copy file
                    shutil.copy2(item, dest_path)
                    self.logger.debug(f"Updated: {relative_path}")

            return True

        except Exception as e:
            self.logger.error(f"Failed to apply update files: {e}")
            return False

    def _restore_backup(self, backup_dir: Path) -> bool:
        """Restore from backup."""
        try:
            import shutil

            self.logger.info("Restoring from backup...")

            for item in backup_dir.rglob('*'):
                if item.is_file():
                    relative_path = item.relative_to(backup_dir)
                    dest_path = PROJECT_ROOT / relative_path

                    # Create parent directories
                    dest_path.parent.mkdir(parents=True, exist_ok=True)

                    # Copy file
                    shutil.copy2(item, dest_path)

            self.logger.info("Backup restored")
            return True

        except Exception as e:
            self.logger.error(f"Failed to restore backup: {e}")
            return False

    def _update_version_info(self, update_dir: Path) -> None:
        """Update version information after successful update."""
        try:
            # Copy new version file
            import shutil
            shutil.copy2(update_dir / "app" / "version.py", PROJECT_ROOT / "app" / "version.py")

            # Reload version module
            import importlib
            if 'app.version' in sys.modules:
                importlib.reload(sys.modules['app.version'])

            self.logger.info("Version information updated")

        except Exception as e:
            self.logger.error(f"Failed to update version info: {e}")


def check_and_apply_updates() -> bool:
    """
    Check for updates and apply if available.

    Returns:
        True if update was applied and restart is needed
    """
    updater = UpdateManager()
    update_available, latest_version, update_info = updater.check_for_updates()

    if update_available and update_info:
        print(f"Update available: {latest_version}")
        print("Downloading update...")

        update_file = updater.download_update(update_info)
        if update_file:
            print("Applying update...")
            if updater.apply_update(update_file):
                print("Update applied successfully. Please restart the application.")
                return True
            else:
                print("Failed to apply update.")
        else:
            print("Failed to download update.")

    return False


def main():
    """Main entry point for update checker."""
    if len(sys.argv) > 1 and sys.argv[1] == "--apply":
        # Apply available updates
        restart_needed = check_and_apply_updates()
        if restart_needed:
            # Restart application
            print("Restarting application...")
            python = sys.executable
            args = [python] + sys.argv[:-1]  # Remove --apply flag
            os.execv(python, args)
    else:
        # Just check for updates
        updater = UpdateManager()
        update_available, latest_version, _ = updater.check_for_updates()

        if update_available:
            print(f"Update available: {latest_version}")
            print("Run with --apply to download and install the update.")
            return 1
        else:
            print("Application is up to date.")
            return 0


if __name__ == "__main__":
    sys.exit(main())