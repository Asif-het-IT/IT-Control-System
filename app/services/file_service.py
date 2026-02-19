# app/services/file_service.py
"""
File system operations service.
"""
import os
import shutil
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
import logging

from app.config.settings import get_config
from app.infrastructure.logger import get_logger
from app.infrastructure.exceptions import FileSystemError

logger = get_logger("file")


class FileService:
    """Service for file system operations."""

    def __init__(self):
        self.config = get_config()

    def ensure_directory(self, path: Path) -> Path:
        """
        Ensure a directory exists, creating it if necessary.

        Args:
            path: Directory path

        Returns:
            The directory path
        """
        try:
            path.mkdir(parents=True, exist_ok=True)
            return path
        except Exception as e:
            raise FileSystemError(f"Failed to create directory {path}: {e}")

    def list_files(
        self,
        directory: Path,
        pattern: str = "*",
        recursive: bool = False
    ) -> List[Path]:
        """
        List files in a directory.

        Args:
            directory: Directory to list
            pattern: File pattern to match
            recursive: Whether to search recursively

        Returns:
            List of file paths
        """
        try:
            if recursive:
                return list(directory.rglob(pattern))
            else:
                return list(directory.glob(pattern))
        except Exception as e:
            logger.error(f"Failed to list files in {directory}: {e}")
            return []

    def calculate_file_hash(self, file_path: Path, algorithm: str = "md5") -> Optional[str]:
        """
        Calculate file hash.

        Args:
            file_path: Path to file
            algorithm: Hash algorithm (md5, sha1, sha256)

        Returns:
            File hash as hex string, or None if error
        """
        try:
            hash_func = getattr(hashlib, algorithm)()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_func.update(chunk)
            return hash_func.hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate hash for {file_path}: {e}")
            return None

    def copy_file(self, src: Path, dst: Path, overwrite: bool = False) -> bool:
        """
        Copy a file.

        Args:
            src: Source file path
            dst: Destination file path
            overwrite: Whether to overwrite existing file

        Returns:
            True if copied successfully, False otherwise
        """
        try:
            if dst.exists() and not overwrite:
                logger.warning(f"Destination file exists, skipping: {dst}")
                return False

            self.ensure_directory(dst.parent)
            shutil.copy2(src, dst)
            logger.info(f"File copied: {src} -> {dst}")
            return True
        except Exception as e:
            logger.error(f"Failed to copy file {src} to {dst}: {e}")
            return False

    def move_file(self, src: Path, dst: Path, overwrite: bool = False) -> bool:
        """
        Move a file.

        Args:
            src: Source file path
            dst: Destination file path
            overwrite: Whether to overwrite existing file

        Returns:
            True if moved successfully, False otherwise
        """
        try:
            if dst.exists() and not overwrite:
                logger.warning(f"Destination file exists, skipping: {dst}")
                return False

            self.ensure_directory(dst.parent)
            shutil.move(str(src), str(dst))
            logger.info(f"File moved: {src} -> {dst}")
            return True
        except Exception as e:
            logger.error(f"Failed to move file {src} to {dst}: {e}")
            return False

    def delete_file(self, file_path: Path) -> bool:
        """
        Delete a file.

        Args:
            file_path: Path to file to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"File deleted: {file_path}")
                return True
            else:
                logger.warning(f"File not found for deletion: {file_path}")
                return False
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
            return False

    def get_file_info(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Get file information.

        Args:
            file_path: Path to file

        Returns:
            Dictionary with file information, or None if error
        """
        try:
            stat = file_path.stat()
            return {
                'path': str(file_path),
                'name': file_path.name,
                'size': stat.st_size,
                'modified': stat.st_mtime,
                'created': stat.st_ctime,
                'is_file': file_path.is_file(),
                'is_dir': file_path.is_dir(),
                'hash': self.calculate_file_hash(file_path)
            }
        except Exception as e:
            logger.error(f"Failed to get file info for {file_path}: {e}")
            return None

    def find_files_by_pattern(
        self,
        directory: Path,
        patterns: List[str],
        recursive: bool = True
    ) -> List[Path]:
        """
        Find files matching patterns.

        Args:
            directory: Directory to search
            patterns: List of glob patterns
            recursive: Whether to search recursively

        Returns:
            List of matching file paths
        """
        files = []
        for pattern in patterns:
            files.extend(self.list_files(directory, pattern, recursive))
        return list(set(files))  # Remove duplicates

    def compare_directories(
        self,
        src_dir: Path,
        dst_dir: Path,
        compare_hashes: bool = False
    ) -> Dict[str, List[Path]]:
        """
        Compare two directories.

        Args:
            src_dir: Source directory
            dst_dir: Destination directory
            compare_hashes: Whether to compare file hashes

        Returns:
            Dictionary with 'only_in_src', 'only_in_dst', 'different' keys
        """
        try:
            src_files = set(self.list_files(src_dir, recursive=True))
            dst_files = set(self.list_files(dst_dir, recursive=True))

            # Make paths relative for comparison
            src_rel = {f.relative_to(src_dir) for f in src_files}
            dst_rel = {f.relative_to(dst_dir) for f in dst_files}

            only_in_src = [src_dir / p for p in (src_rel - dst_rel)]
            only_in_dst = [dst_dir / p for p in (dst_rel - src_rel)]

            different = []
            if compare_hashes:
                common = src_rel & dst_rel
                for rel_path in common:
                    src_file = src_dir / rel_path
                    dst_file = dst_dir / rel_path
                    if self.calculate_file_hash(src_file) != self.calculate_file_hash(dst_file):
                        different.append(src_file)

            return {
                'only_in_src': only_in_src,
                'only_in_dst': only_in_dst,
                'different': different
            }

        except Exception as e:
            logger.error(f"Failed to compare directories {src_dir} and {dst_dir}: {e}")
            return {'only_in_src': [], 'only_in_dst': [], 'different': []}


# Global file service instance
_file_service = None

def get_file_service() -> FileService:
    """Get the global file service instance."""
    global _file_service
    if _file_service is None:
        _file_service = FileService()
    return _file_service