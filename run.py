#!/usr/bin/env python3
"""
HET IT Control System - Main Entry Point
"""
import sys
import argparse
from pathlib import Path

# Add app to path
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

from app.config.settings import get_config
from app.infrastructure.logger import setup_logging
from app.infrastructure.database import get_db_manager
from app.infrastructure.scheduler import get_scheduler
from app.api.main import app as fastapi_app
from app.ui.main_window import main as gui_main
import uvicorn


def setup_application():
    """Setup application components."""
    config = get_config()

    # Setup logging
    setup_logging(
        log_level=config.logging.level,
        log_dir=config.paths.logs_dir,
        max_bytes=config.logging.max_bytes,
        backup_count=config.logging.backup_count
    )

    # Initialize database
    db_manager = get_db_manager()
    db_manager.initialize()

    # Initialize scheduler
    scheduler = get_scheduler()
    scheduler.initialize()


def run_api(host: str = None, port: int = None, debug: bool = None):
    """Run the FastAPI server."""
    config = get_config()

    host = host or config.api.host
    port = port or config.api.port
    debug = debug if debug is not None else config.api.debug

    print(f"Starting HET IT Control System API on {host}:{port}")
    uvicorn.run(
        "app.api.main:app",
        host=host,
        port=port,
        reload=debug
    )


def run_gui():
    """Run the GUI application."""
    print("Starting HET IT Control System GUI")
    gui_main()


def run_scheduler():
    """Run the scheduler service."""
    scheduler = get_scheduler()
    scheduler.start()

    print("Scheduler started. Press Ctrl+C to stop.")
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping scheduler...")
        scheduler.stop()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="HET IT Control System")
    parser.add_argument(
        "mode",
        choices=["api", "gui", "scheduler", "setup"],
        help="Run mode"
    )
    parser.add_argument("--host", help="API host (for api mode)")
    parser.add_argument("--port", type=int, help="API port (for api mode)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    args = parser.parse_args()

    # Setup application
    setup_application()

    # Run selected mode
    if args.mode == "api":
        run_api(host=args.host, port=args.port, debug=args.debug)
    elif args.mode == "gui":
        run_gui()
    elif args.mode == "scheduler":
        run_scheduler()
    elif args.mode == "setup":
        print("Application setup completed successfully!")
        print(f"Configuration loaded from: {get_config().config_dir}")
        print(f"Database initialized at: {get_config().database.url}")
        print(f"Logs directory: {get_config().paths.logs_dir}")


if __name__ == "__main__":
    main()