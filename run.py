#!/usr/bin/env python3
"""
HET IT Control System - Main Entry Point
Enterprise-grade application launcher with proper error handling
"""

import sys
import argparse
from pathlib import Path
import traceback

# Ensure project root in path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import core components with error handling
try:
    from app.config.settings import get_config
    from app.infrastructure.logger import setup_logging
    from app.infrastructure.database import get_db_manager
    from app.infrastructure.scheduler import get_scheduler
    from app.services.email_service import get_email_service
    from app.ui.main_window import main as gui_main
    from app.infrastructure.job_history_db import init_db as init_job_history_db
    from app.infrastructure.shutdown import get_shutdown_manager, register_shutdown_callback, ShutdownPhase, shutdown_context
    from app.infrastructure.exceptions import get_global_exception_handler
except ImportError as e:
    print(f"CRITICAL: Failed to import required modules: {e}")
    print("Please ensure all dependencies are installed and the project structure is correct.")
    sys.exit(1)


def setup_application():
    """Setup application components with comprehensive error handling."""
    try:
        print("🔧 Initializing HET IT Control System...")

        # Get configuration
        config = get_config()
        print(f"✓ Configuration loaded from: {config.__class__.__name__}")

        # Setup logging
        setup_logging(
            log_level=config.logging.level,
            log_dir=config.paths.logs_dir,
            max_bytes=config.logging.max_bytes,
            backup_count=config.logging.backup_count
        )
        print("✓ Logging system initialized")

        # Initialize database
        db_manager = get_db_manager()
        db_manager.initialize()
        print("✓ Main database initialized")

        # Initialize job history database
        init_job_history_db()
        print("✓ Job history database initialized")

        # Initialize scheduler
        scheduler = get_scheduler()
        scheduler.initialize()
        print("✓ Job scheduler initialized")

        # Register shutdown callbacks
        shutdown_manager = get_shutdown_manager()

        # Stop services first
        register_shutdown_callback(ShutdownPhase.STOP_SERVICES, scheduler.stop, priority=100)
        register_shutdown_callback(ShutdownPhase.STOP_SERVICES,
                                 lambda: print("🛑 Stopping scheduler service..."), priority=99)

        # Close connections
        register_shutdown_callback(ShutdownPhase.CLOSE_CONNECTIONS, db_manager.close, priority=100)
        register_shutdown_callback(ShutdownPhase.CLOSE_CONNECTIONS,
                                 lambda: print("🔌 Closing database connections..."), priority=99)

        # Cleanup resources
        register_shutdown_callback(ShutdownPhase.CLEANUP_RESOURCES,
                                 lambda: print("🧹 Cleaning up application resources..."), priority=50)

        # Finalize
        register_shutdown_callback(ShutdownPhase.FINALIZE,
                                 lambda: print("✅ Application shutdown completed"), priority=10)

        print("✓ Shutdown handlers registered")

        print("🎉 Application setup completed successfully!")
        return True

    except Exception as e:
        print(f"❌ CRITICAL: Application setup failed: {e}")
        traceback.print_exc()
        return False


def run_gui():
    """Run the GUI application."""
    try:
        print("🚀 Starting HET IT Control System GUI...")
        gui_main()
    except Exception as e:
        print(f"❌ CRITICAL: GUI failed to start: {e}")
        traceback.print_exc()
        sys.exit(1)


def run_api(host: str = None, port: int = None, debug: bool = None):
    """Run the FastAPI server."""
    try:
        config = get_config()
        host = host or config.api.host
        port = port or config.api.port
        debug = debug if debug is not None else config.api.debug

        print(f"🌐 Starting HET IT Control System API on {host}:{port}")
        import uvicorn
        uvicorn.run(
            "app.api.main:app",
            host=host,
            port=port,
            reload=debug
        )
    except Exception as e:
        print(f"❌ CRITICAL: API server failed to start: {e}")
        traceback.print_exc()
        sys.exit(1)


def run_scheduler():
    """Run the scheduler service."""
    try:
        scheduler = get_scheduler()
        scheduler.start()
        print("⏰ Scheduler started. Press Ctrl+C to stop.")
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("🛑 Stopping scheduler...")
        scheduler.stop()
    except Exception as e:
        print(f"❌ CRITICAL: Scheduler failed: {e}")
        traceback.print_exc()
        sys.exit(1)


def run_service():
    """Run the Windows service."""
    try:
        print("🔧 Starting HET IT Control System Windows Service...")
        from service.het_service import main as service_main
        service_main()
    except Exception as e:
        print(f"❌ CRITICAL: Service failed to start: {e}")
        traceback.print_exc()
        sys.exit(1)


def run_setup():
    """Run the setup wizard."""
    try:
        print("⚙️ Starting HET IT Control System Setup Wizard...")
        from setup.setup_wizard import main as setup_main
        setup_main()
    except Exception as e:
        print(f"❌ CRITICAL: Setup wizard failed to start: {e}")
        traceback.print_exc()
        sys.exit(1)


def test_email():
    """Test email configuration."""
    try:
        print("📧 Testing email configuration...")
        email_service = get_email_service()

        # Test connection
        if email_service.test_connection():
            print("✅ SMTP connection successful")

            # Send test email
            success = email_service.send_email(
                subject="HET IT Control System - Email Test",
                body="This is a test email from the HET IT Control System.\n\nIf you received this email, the email configuration is working correctly.",
                recipients=email_service.config.recipients
            )

            if success:
                print("✅ Test email sent successfully")
            else:
                print("❌ Failed to send test email")
        else:
            print("❌ SMTP connection failed")
            print("Please check your email configuration in the .env file")
    except Exception as e:
        print(f"❌ Email test failed: {e}")
        traceback.print_exc()


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="HET IT Control System - Enterprise Automation Dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python run.py gui              # Start GUI application
  python run.py api              # Start API server
  python run.py scheduler        # Start scheduler service (console)
  python run.py service          # Start Windows service
  python run.py setup            # Run setup wizard
  python run.py test-email       # Test email configuration
  python run.py api --host 0.0.0.0 --port 8080  # Custom API settings
        """
    )

    parser.add_argument(
        "mode",
        choices=["api", "gui", "scheduler", "service", "setup", "test-email"],
        help="Run mode"
    )
    parser.add_argument("--host", help="API host (for api mode)")
    parser.add_argument("--port", type=int, help="API port (for api mode)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    args = parser.parse_args()

    # Setup application (except for setup mode which does it internally)
    if args.mode != "setup":
        if not setup_application():
            print("❌ Application setup failed. Cannot continue.")
            sys.exit(1)

    # Use shutdown context for graceful shutdown
    shutdown_manager = get_shutdown_manager()

    with shutdown_context() as manager:
        try:
            if args.mode == "api":
                run_api(host=args.host, port=args.port, debug=args.debug)
            elif args.mode == "gui":
                run_gui()
            elif args.mode == "scheduler":
                run_scheduler()
            elif args.mode == "service":
                run_service()
            elif args.mode == "setup":
                run_setup()
            elif args.mode == "test-email":
                test_email()
        except KeyboardInterrupt:
            print("\n👋 Application stopped by user")
            shutdown_manager.initiate_shutdown("keyboard_interrupt")
        except Exception as e:
            print(f"❌ Unexpected error in {args.mode} mode: {e}")
            traceback.print_exc()
            shutdown_manager.initiate_shutdown("unexpected_error")
            sys.exit(1)

    # Wait for shutdown to complete
    if shutdown_manager.wait_for_shutdown(timeout=35.0):  # 30s graceful + 5s force
        print("👋 Application shutdown completed successfully")
    else:
        print("⚠️  Application shutdown timed out")
        sys.exit(1)


if __name__ == "__main__":
    main()