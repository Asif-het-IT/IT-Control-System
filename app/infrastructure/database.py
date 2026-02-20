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

from app.config.settings import get_config

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
        """Get database connection with error handling."""
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=30.0)
            conn.row_factory = sqlite3.Row
            yield conn
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e):
                logger.warning("Database locked, retrying...")
                # Try to recover from lock
                self._recover_from_lock()
                # Retry once
                try:
                    if conn:
                        conn.close()
                    conn = sqlite3.connect(str(self.db_path), timeout=30.0)
                    conn.row_factory = sqlite3.Row
                    yield conn
                except Exception as e2:
                    logger.error(f"Database recovery failed: {e2}")
                    raise
            else:
                raise
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def _recover_from_lock(self):
        """Attempt to recover from database lock."""
        try:
            # Try to remove WAL and SHM files
            wal_file = self.db_path.with_suffix('.db-wal')
            shm_file = self.db_path.with_suffix('.db-shm')

            if wal_file.exists():
                wal_file.unlink()
                logger.info("Removed WAL file to recover from lock")

            if shm_file.exists():
                shm_file.unlink()
                logger.info("Removed SHM file to recover from lock")

        except Exception as e:
            logger.error(f"Failed to recover from database lock: {e}")

    def create_backup(self) -> Optional[str]:
        """Create daily backup of database."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"het_control_backup_{timestamp}.db"
            backup_path = self.backup_dir / backup_name

            # Copy database file
            shutil.copy2(self.db_path, backup_path)

            # Clean old backups (keep last 7 days)
            self._cleanup_old_backups()

            logger.info(f"Database backup created: {backup_path}")
            return str(backup_path)

        except Exception as e:
            logger.error(f"Failed to create database backup: {e}")
            return None

    def _cleanup_old_backups(self):
        """Remove backups older than 7 days."""
        try:
            cutoff_date = datetime.now().timestamp() - (7 * 24 * 60 * 60)  # 7 days

            for backup_file in self.backup_dir.glob("het_control_backup_*.db"):
                if backup_file.stat().st_mtime < cutoff_date:
                    backup_file.unlink()
                    logger.info(f"Removed old backup: {backup_file}")

        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")

    def get_db_size(self) -> int:
        """Get database file size in bytes."""
        try:
            return self.db_path.stat().st_size
        except Exception:
            return 0

    def optimize(self):
        """Optimize database performance."""
        try:
            with self.get_connection() as conn:
                conn.execute("VACUUM")
                conn.execute("REINDEX")
                logger.info("Database optimized")
        except Exception as e:
            logger.error(f"Failed to optimize database: {e}")


# Global instance
_db_manager = None

def get_database_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


class Branch(Base):
    """Branch configuration."""
    __tablename__ = "branches"

    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    nas_base = Column(String(500))
    tally_base = Column(String(500))
    laundry_base = Column(String(500))
    qsync_exe = Column(String(500))
    email_recipients = Column(JSON)
    speed_test_enabled = Column(Boolean, default=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Report(Base):
    """Generated reports."""
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    branch_id = Column(String(50), nullable=False, index=True)
    job_name = Column(String(100), nullable=False, index=True)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    content_type = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class SystemMetric(Base):
    """System metrics."""
    __tablename__ = "system_metrics"

    id = Column(Integer, primary_key=True)
    metric_name = Column(String(100), nullable=False, index=True)
    branch_id = Column(String(50), nullable=False, index=True)
    value = Column(Float, nullable=False)
    unit = Column(String(20))
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class DatabaseManager:
    """Database connection and session management."""

    def __init__(self):
        self.config = get_config()
        self.engine = None
        self.SessionLocal = None
        self._initialized = False

    def initialize(self):
        """Initialize database connection."""
        if self._initialized:
            return

        try:
            self.engine = create_engine(
                self.config.database.url,
                echo=self.config.database.echo,
                pool_size=self.config.database.pool_size,
                max_overflow=self.config.database.max_overflow
            )

            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )

            # Create tables
            Base.metadata.create_all(bind=self.engine)

            self._initialized = True
            logger.info("Database initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def get_session(self):
        """Get database session."""
        if not self._initialized:
            self.initialize()
        return self.SessionLocal()

    def close(self):
        """Close database connections."""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connections closed")


# Global database manager
_db_manager = None

def get_db_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager

def get_db():
    """Get database session (for FastAPI dependency injection)."""
    db = get_db_manager().get_session()
    try:
        yield db
    finally:
        db.close()