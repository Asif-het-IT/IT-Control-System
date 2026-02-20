# app/infrastructure/database.py
"""
SQLite database infrastructure with safety features.
"""

import sqlite3
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
from contextlib import contextmanager
import logging

# SQLAlchemy imports for ORM models
from sqlalchemy import create_engine, Column, String, Boolean, DateTime, JSON, Integer, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

Base = declarative_base()


class DatabaseManager:
    """Safe SQLite database manager with WAL mode and backups."""

    def __init__(self, db_path: str = "database/het_control.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.backup_dir = self.db_path.parent / "backups"
        self.backup_dir.mkdir(exist_ok=True)

        # Enable WAL mode for better concurrency
        self._enable_wal_mode()

    def _enable_wal_mode(self):
        """Enable WAL mode for better performance and concurrency."""
        try:
            with self.get_connection() as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
                conn.execute("PRAGMA temp_store=MEMORY")
                logger.info("SQLite WAL mode enabled")
        except Exception as e:
            logger.error(f"Failed to enable WAL mode: {e}")

    @contextmanager
    def get_connection(self):
        """Get database connection with proper cleanup."""
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            yield conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def create_backup(self) -> bool:
        """Create database backup."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"het_control_backup_{timestamp}.db"

            with self.get_connection() as conn:
                # Use SQLite backup API for safe backup
                backup_conn = sqlite3.connect(str(backup_path))
                conn.backup(backup_conn)
                backup_conn.close()

            # Clean old backups (keep last 7)
            self._cleanup_old_backups()

            logger.info(f"Database backup created: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            return False

    def _cleanup_old_backups(self):
        """Clean up old backup files."""
        try:
            backups = sorted(self.backup_dir.glob("het_control_backup_*.db"))
            if len(backups) > 7:
                for old_backup in backups[:-7]:
                    old_backup.unlink()
                    logger.info(f"Removed old backup: {old_backup}")
        except Exception as e:
            logger.error(f"Backup cleanup failed: {e}")

    def get_db_size(self) -> int:
        """Get database file size in bytes."""
        try:
            return self.db_path.stat().st_size
        except Exception:
            return 0

    def optimize_database(self) -> bool:
        """Optimize database performance."""
        try:
            with self.get_connection() as conn:
                conn.execute("VACUUM")
                conn.execute("REINDEX")
                logger.info("Database optimized")
                return True
        except Exception as e:
            logger.error(f"Database optimization failed: {e}")
            return False


# Global instance
_db_manager = None

def get_database_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager