# app/infrastructure/logging.py
"""
Logging infrastructure for HET IT Control System.
Separate logs for service and GUI modes.
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional

# Constants
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

SERVICE_LOG_FILE = LOG_DIR / "het_service.log"
GUI_LOG_FILE = LOG_DIR / "het_gui.log"

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
MAX_BYTES = 10 * 1024 * 1024  # 10MB
BACKUP_COUNT = 5


def setup_service_logging(level: str = "INFO") -> logging.Logger:
    """Setup logging for Windows service mode."""
    logger = logging.getLogger("het_service")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Rotating file handler for service
    handler = logging.handlers.RotatingFileHandler(
        SERVICE_LOG_FILE,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT
    )
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(handler)

    # Console handler for debugging
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(console)

    return logger


def setup_gui_logging(level: str = "INFO") -> logging.Logger:
    """Setup logging for GUI mode."""
    logger = logging.getLogger("het_gui")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Rotating file handler for GUI
    handler = logging.handlers.RotatingFileHandler(
        GUI_LOG_FILE,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT
    )
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(handler)

    # Console handler for GUI output
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(console)

    return logger


def get_service_logger() -> logging.Logger:
    """Get the service logger."""
    return logging.getLogger("het_service")


def get_gui_logger() -> logging.Logger:
    """Get the GUI logger."""
    return logging.getLogger("het_gui")


# Global loggers
_service_logger = None
_gui_logger = None

def init_logging(mode: str = "service", level: str = "INFO"):
    """Initialize logging based on mode."""
    global _service_logger, _gui_logger

    if mode == "service":
        _service_logger = setup_service_logging(level)
        return _service_logger
    elif mode == "gui":
        _gui_logger = setup_gui_logging(level)
        return _gui_logger
    else:
        raise ValueError(f"Unknown logging mode: {mode}")