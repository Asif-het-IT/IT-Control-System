# app/infrastructure/database.py
"""
Database setup and models for the HET IT Control System.
"""
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, Float, JSON, ForeignKey
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from app.config.settings import get_config
from app.infrastructure.logger import get_logger

Base = declarative_base()
logger = get_logger("database")

class JobExecution(Base):
    """Job execution history."""
    __tablename__ = "job_executions"

    id = Column(Integer, primary_key=True)
    job_name = Column(String(100), nullable=False, index=True)
    branch_id = Column(String(50), nullable=False, index=True)
    status = Column(String(20), nullable=False)
    success = Column(Boolean, nullable=False)
    error_message = Column(Text)
    execution_time = Column(Float)
    retry_count = Column(Integer, default=0)
    metrics = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to job logs
    logs = relationship("JobLog", back_populates="execution", cascade="all, delete-orphan")


class JobLog(Base):
    """Job execution logs."""
    __tablename__ = "job_logs"

    id = Column(Integer, primary_key=True)
    execution_id = Column(Integer, ForeignKey("job_executions.id"), nullable=False, index=True)
    level = Column(String(10), nullable=False)
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationship back to execution
    execution = relationship("JobExecution", back_populates="logs")


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