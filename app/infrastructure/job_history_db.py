# app/infrastructure/job_history_db.py
"""
Production-grade Job History Database with SQLite optimizations.
Features:
- WAL mode for better concurrency
- Automatic history cleanup based on retention policy
- Optimized indexing for performance
- Connection pooling and error handling
- Database maintenance and vacuum operations
"""

from __future__ import annotations
import sqlite3
import threading
import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict, Any
from contextlib import contextmanager
import logging

from app.config.settings import get_config
from app.infrastructure.logger import get_database_logger
from app.infrastructure.exceptions import DatabaseError, safe_call

logger = get_database_logger()

# Thread-local storage for connections
_local = threading.local()

class JobHistoryDB:
    """Production-grade job history database manager."""

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize database manager.

        Args:
            db_path: Path to database file
        """
        self.config = get_config()
        self.db_path = db_path or self.config.paths.database_dir / "job_history.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Database settings
        self._connection_pool = {}
        self._pool_lock = threading.RLock()
        self._maintenance_lock = threading.Lock()

        # Initialize database
        self._initialize_database()

    def _initialize_database(self) -> None:
        """Initialize database with optimized settings."""
        with self._get_connection() as conn:
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA cache_size=-64000;")  # 64MB cache
            conn.execute("PRAGMA temp_store=MEMORY;")
            conn.execute("PRAGMA mmap_size=268435456;")  # 256MB memory map
            conn.execute("PRAGMA foreign_keys=ON;")

            # Create tables
            self._create_tables(conn)

            # Create indexes
            self._create_indexes(conn)

            conn.commit()

    def _create_tables(self, conn: sqlite3.Connection) -> None:
        """Create database tables."""
        # Main job history table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS job_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                branch TEXT NOT NULL DEFAULT 'default',
                status TEXT NOT NULL,
                duration REAL NOT NULL DEFAULT 0.0,
                message TEXT,
                error_details TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                retry_count INTEGER DEFAULT 0,
                metadata TEXT  -- JSON field for additional data
            );
        """)

        # Job statistics table for performance monitoring
        conn.execute("""
            CREATE TABLE IF NOT EXISTS job_statistics (
                job_id TEXT PRIMARY KEY,
                total_runs INTEGER DEFAULT 0,
                successful_runs INTEGER DEFAULT 0,
                failed_runs INTEGER DEFAULT 0,
                average_duration REAL DEFAULT 0.0,
                last_run TEXT,
                last_success TEXT,
                last_failure TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)

        # Database maintenance log
        conn.execute("""
            CREATE TABLE IF NOT EXISTS maintenance_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation TEXT NOT NULL,
                details TEXT,
                duration REAL,
                created_at TEXT NOT NULL
            );
        """)

    def _create_indexes(self, conn: sqlite3.Connection) -> None:
        """Create optimized indexes."""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_job_history_job_id ON job_history(job_id);",
            "CREATE INDEX IF NOT EXISTS idx_job_history_status ON job_history(status);",
            "CREATE INDEX IF NOT EXISTS idx_job_history_branch ON job_history(branch);",
            "CREATE INDEX IF NOT EXISTS idx_job_history_created_at ON job_history(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_job_history_composite ON job_history(job_id, status, created_at);",
            "CREATE INDEX IF NOT EXISTS idx_job_statistics_job_id ON job_statistics(job_id);",
            "CREATE INDEX IF NOT EXISTS idx_maintenance_log_created_at ON maintenance_log(created_at);"
        ]

        for index_sql in indexes:
            conn.execute(index_sql)

    @contextmanager
    def _get_connection(self) -> sqlite3.Connection:
        """Get a thread-local database connection."""
        conn = getattr(_local, 'connection', None)
        if conn is None:
            try:
                conn = sqlite3.connect(str(self.db_path), timeout=30.0, check_same_thread=False)
                conn.row_factory = sqlite3.Row  # Enable column access by name
                _local.connection = conn
            except sqlite3.Error as e:
                raise DatabaseError(f"Failed to connect to database: {e}")

        try:
            yield conn
        except Exception:
            # Reset connection on error
            if hasattr(_local, 'connection'):
                delattr(_local, 'connection')
            raise

    def log_job(
        self,
        job_id: str,
        status: str,
        message: str = "",
        duration: float = 0.0,
        branch: str = "default",
        error_details: Optional[str] = None,
        retry_count: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Log a job execution.

        Args:
            job_id: Unique job identifier
            status: Job status (SUCCESS, FAILED, RUNNING, etc.)
            message: Log message
            duration: Execution duration in seconds
            branch: Branch name
            error_details: Detailed error information
            retry_count: Number of retries attempted
            metadata: Additional metadata as dict

        Returns:
            Inserted row ID
        """
        operation_start = time.time()

        try:
            ts = datetime.now().isoformat()
            msg = (message or "")[:5000]  # Truncate long messages
            error_det = (error_details or "")[:10000] if error_details else None
            meta_json = json.dumps(metadata) if metadata else None

            with self._get_connection() as conn:
                cursor = conn.execute("""
                    INSERT INTO job_history(
                        job_id, branch, status, duration, message,
                        error_details, created_at, retry_count, metadata
                    ) VALUES (?,?,?,?,?,?,?,?,?)
                """, (job_id, branch, status.upper(), float(duration), msg,
                      error_det, ts, retry_count, meta_json))

                job_history_id = cursor.lastrowid

                # Update statistics
                self._update_job_statistics(conn, job_id, status, duration, ts)

                conn.commit()

                operation_duration = time.time() - operation_start
                logger.log_performance("log_job", operation_duration, job_id=job_id, status=status)

                return job_history_id

        except sqlite3.Error as e:
            operation_duration = time.time() - operation_start
            logger.error(f"Failed to log job {job_id}: {e}", extra={"duration": operation_duration})
            raise DatabaseError(f"Failed to log job: {e}")

    def _update_job_statistics(self, conn: sqlite3.Connection, job_id: str,
                              status: str, duration: float, timestamp: str) -> None:
        """Update job statistics."""
        try:
            # Check if statistics record exists
            cursor = conn.execute("SELECT * FROM job_statistics WHERE job_id = ?", (job_id,))
            existing = cursor.fetchone()

            if existing:
                # Update existing record
                total_runs = existing['total_runs'] + 1
                successful_runs = existing['successful_runs'] + (1 if status == 'SUCCESS' else 0)
                failed_runs = existing['failed_runs'] + (1 if status == 'FAILED' else 0)

                # Recalculate average duration
                old_avg = existing['average_duration']
                old_total = existing['total_runs']
                new_avg = ((old_avg * old_total) + duration) / total_runs

                update_data = {
                    'total_runs': total_runs,
                    'successful_runs': successful_runs,
                    'failed_runs': failed_runs,
                    'average_duration': new_avg,
                    'last_run': timestamp,
                    'updated_at': timestamp
                }

                if status == 'SUCCESS':
                    update_data['last_success'] = timestamp
                elif status == 'FAILED':
                    update_data['last_failure'] = timestamp

                conn.execute("""
                    UPDATE job_statistics SET
                        total_runs = ?, successful_runs = ?, failed_runs = ?,
                        average_duration = ?, last_run = ?, last_success = ?,
                        last_failure = ?, updated_at = ?
                    WHERE job_id = ?
                """, (
                    update_data['total_runs'], update_data['successful_runs'],
                    update_data['failed_runs'], update_data['average_duration'],
                    update_data['last_run'], update_data.get('last_success'),
                    update_data.get('last_failure'), update_data['updated_at'], job_id
                ))
            else:
                # Create new statistics record
                conn.execute("""
                    INSERT INTO job_statistics(
                        job_id, total_runs, successful_runs, failed_runs,
                        average_duration, last_run, last_success, last_failure,
                        created_at, updated_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?)
                """, (
                    job_id, 1,
                    1 if status == 'SUCCESS' else 0,
                    1 if status == 'FAILED' else 0,
                    duration, timestamp,
                    timestamp if status == 'SUCCESS' else None,
                    timestamp if status == 'FAILED' else None,
                    timestamp, timestamp
                ))

        except sqlite3.Error as e:
            logger.warning(f"Failed to update job statistics for {job_id}: {e}")

    def get_last_run(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the last run information for a job.

        Args:
            job_id: Job identifier

        Returns:
            Dictionary with run information or None
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT status, duration, created_at, branch, message, error_details, retry_count
                    FROM job_history
                    WHERE job_id = ?
                    ORDER BY id DESC LIMIT 1
                """, (job_id,))

                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None

        except sqlite3.Error as e:
            logger.error(f"Failed to get last run for job {job_id}: {e}")
            raise DatabaseError(f"Failed to get last run: {e}")

    def get_history(self, job_id: Optional[str] = None, limit: int = 50,
                   status: Optional[str] = None, branch: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get job execution history.

        Args:
            job_id: Filter by job ID
            limit: Maximum number of records
            status: Filter by status
            branch: Filter by branch

        Returns:
            List of history records
        """
        try:
            query = """
                SELECT created_at, job_id, branch, duration, status, message, error_details, retry_count
                FROM job_history
                WHERE 1=1
            """
            params = []

            if job_id:
                query += " AND job_id = ?"
                params.append(job_id)

            if status:
                query += " AND status = ?"
                params.append(status.upper())

            if branch:
                query += " AND branch = ?"
                params.append(branch)

            query += " ORDER BY id DESC LIMIT ?"
            params.append(limit)

            with self._get_connection() as conn:
                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]

        except sqlite3.Error as e:
            logger.error(f"Failed to get job history: {e}")
            raise DatabaseError(f"Failed to get job history: {e}")

    def get_job_statistics(self, job_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get job statistics.

        Args:
            job_id: Specific job ID or None for all

        Returns:
            List of statistics records
        """
        try:
            with self._get_connection() as conn:
                if job_id:
                    cursor = conn.execute("SELECT * FROM job_statistics WHERE job_id = ?", (job_id,))
                else:
                    cursor = conn.execute("SELECT * FROM job_statistics ORDER BY updated_at DESC")

                return [dict(row) for row in cursor.fetchall()]

        except sqlite3.Error as e:
            logger.error(f"Failed to get job statistics: {e}")
            raise DatabaseError(f"Failed to get job statistics: {e}")

    def cleanup_history(self, retention_days: Optional[int] = None) -> int:
        """
        Clean up old job history records.

        Args:
            retention_days: Days to retain (uses config default if None)

        Returns:
            Number of records deleted
        """
        if retention_days is None:
            retention_days = self.config.database.history_retention_days

        cutoff_date = datetime.now() - timedelta(days=retention_days)
        cutoff_str = cutoff_date.isoformat()

        operation_start = time.time()

        try:
            with self._get_connection() as conn:
                # Get count before deletion
                cursor = conn.execute("SELECT COUNT(*) FROM job_history WHERE created_at < ?", (cutoff_str,))
                count_before = cursor.fetchone()[0]

                # Delete old records
                conn.execute("DELETE FROM job_history WHERE created_at < ?", (cutoff_str,))
                deleted_count = conn.total_changes

                # Log maintenance operation
                duration = time.time() - operation_start
                conn.execute("""
                    INSERT INTO maintenance_log(operation, details, duration, created_at)
                    VALUES (?, ?, ?, ?)
                """, ("cleanup_history", f"Deleted {deleted_count} records older than {retention_days} days",
                      duration, datetime.now().isoformat()))

                conn.commit()

                logger.info(f"Cleaned up {deleted_count} old job history records",
                           extra={"operation": "cleanup_history", "deleted_count": deleted_count,
                                 "duration": duration})

                return deleted_count

        except sqlite3.Error as e:
            operation_duration = time.time() - operation_start
            logger.error(f"Failed to cleanup job history: {e}", extra={"duration": operation_duration})
            raise DatabaseError(f"Failed to cleanup job history: {e}")

    def vacuum_database(self) -> None:
        """Rebuild database file and reclaim space."""
        operation_start = time.time()

        try:
            with self._get_connection() as conn:
                conn.execute("VACUUM;")

                duration = time.time() - operation_start

                # Log maintenance operation
                conn.execute("""
                    INSERT INTO maintenance_log(operation, details, duration, created_at)
                    VALUES (?, ?, ?, ?)
                """, ("vacuum", "Database vacuum operation", duration, datetime.now().isoformat()))

                conn.commit()

                logger.info("Database vacuum completed", extra={"operation": "vacuum", "duration": duration})

        except sqlite3.Error as e:
            operation_duration = time.time() - operation_start
            logger.error(f"Failed to vacuum database: {e}", extra={"duration": operation_duration})
            raise DatabaseError(f"Failed to vacuum database: {e}")

    def clear_history(self, job_id: Optional[str] = None) -> int:
        """
        Clear job history (use with caution).

        Args:
            job_id: Specific job ID or None for all history

        Returns:
            Number of records deleted
        """
        operation_start = time.time()

        try:
            with self._get_connection() as conn:
                if job_id:
                    conn.execute("DELETE FROM job_history WHERE job_id = ?", (job_id,))
                    # Also remove statistics
                    conn.execute("DELETE FROM job_statistics WHERE job_id = ?", (job_id,))
                else:
                    # Clear all history
                    conn.execute("DELETE FROM job_history")
                    conn.execute("DELETE FROM job_statistics")

                deleted_count = conn.total_changes
                conn.commit()

                duration = time.time() - operation_start
                logger.warning(f"Cleared {deleted_count} job history records",
                              extra={"operation": "clear_history", "job_id": job_id,
                                    "deleted_count": deleted_count, "duration": duration})

                return deleted_count

        except sqlite3.Error as e:
            operation_duration = time.time() - operation_start
            logger.error(f"Failed to clear job history: {e}", extra={"duration": operation_duration})
            raise DatabaseError(f"Failed to clear job history: {e}")

    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            with self._get_connection() as conn:
                stats = {}

                # Table sizes
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """)

                for row in cursor:
                    table_name = row[0]
                    size_cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
                    stats[f"{table_name}_count"] = size_cursor.fetchone()[0]

                # Database file size
                db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
                stats['database_size_bytes'] = db_size
                stats['database_size_mb'] = db_size / (1024 * 1024)

                return stats

        except (sqlite3.Error, OSError) as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}


# Global instance
_job_history_db = None

def get_job_history_db() -> JobHistoryDB:
    """Get the global job history database instance."""
    global _job_history_db
    if _job_history_db is None:
        _job_history_db = JobHistoryDB()
    return _job_history_db

# Backward compatibility functions
def init_db() -> None:
    """Initialize the job history database (backward compatibility)."""
    get_job_history_db()

def log_job(job_id: str, status: str, message: str = "", duration: float = 0.0, branch: str = "default") -> None:
    """Log a job execution (backward compatibility)."""
    get_job_history_db().log_job(job_id, status, message, duration, branch)

def get_last_run(job_id: str) -> Optional[Tuple[str, float, str, str]]:
    """Get last run information (backward compatibility)."""
    result = get_job_history_db().get_last_run(job_id)
    if result:
        return (result['status'], result['duration'], result['created_at'], result['branch'])
    return None

def get_history(job_id: Optional[str] = None, limit: int = 50) -> List[Tuple[str, str, str, float, str, str]]:
    """Get job history (backward compatibility)."""
    results = get_job_history_db().get_history(job_id, limit)
    return [(r['created_at'], r['job_id'], r['branch'], r['duration'], r['status'], r['message']) for r in results]

def clear_history(job_id: Optional[str] = None) -> None:
    """Clear job history (backward compatibility)."""
    get_job_history_db().clear_history(job_id)