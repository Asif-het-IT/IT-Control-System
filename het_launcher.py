#!/usr/bin/env python3
"""
HET IT Control System - Professional Launcher
Handles updates, service management, and application launching
"""

import sys
import os
import argparse
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def check_and_update():
    """Check for updates and apply if available."""
    try:
        from updater.update_manager import check_and_apply_updates
        restart_needed = check_and_apply_updates()
        if restart_needed:
            print("Update applied. Please restart the application.")
            sys.exit(0)
    except ImportError:
        print("Update system not available, continuing...")
    except Exception as e:
        print(f"Update check failed: {e}, continuing...")

def main():
    """Main launcher entry point."""
    parser = argparse.ArgumentParser(
        description="HET IT Control System - Professional Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Professional Windows Application Launcher

MODES:
  gui              Start GUI application
  service          Windows service management
  setup            Run setup wizard
  update           Check for updates
  version          Show version information

SERVICE MANAGEMENT:
  service install    Install Windows service
  service uninstall  Uninstall Windows service
  service start      Start Windows service
  service stop       Stop Windows service
  service status     Show service status

EXAMPLES:
  het_control.exe gui              # Start GUI
  het_control.exe service install  # Install service
  het_control.exe setup            # Run setup wizard
  het_control.exe update           # Check for updates
        """
    )

    parser.add_argument("mode", help="Run mode")
    parser.add_argument("submode", nargs="?", help="Sub-mode for service management")
    parser.add_argument("--skip-update", action="store_true", help="Skip update check")

    args = parser.parse_args()

    # Check for updates unless skipped
    if not args.skip_update and args.mode not in ["update", "version"]:
        check_and_update()

    # Handle different modes
    if args.mode == "gui":
        # Launch GUI
        from run import run_gui
        run_gui()

    elif args.mode == "service":
        if args.submode == "install":
            # Install Windows service
            from service.het_service import main as service_main
            sys.argv = ["het_service.py", "install"]
            service_main()
        elif args.submode == "uninstall":
            # Uninstall Windows service
            from service.het_service import main as service_main
            sys.argv = ["het_service.py", "remove"]
            service_main()
        elif args.submode == "start":
            # Start Windows service
            from service.het_service import main as service_main
            sys.argv = ["het_service.py", "start"]
            service_main()
        elif args.submode == "stop":
            # Stop Windows service
            from service.het_service import main as service_main
            sys.argv = ["het_service.py", "stop"]
            service_main()
        elif args.submode == "status":
            # Show service status
            os.system('sc query "HETITControlSystem"')
        else:
            # Run service directly (for debugging)
            from run import run_service
            run_service()

    elif args.mode == "setup":
        # Run setup wizard
        from run import run_setup
        run_setup()

    elif args.mode == "update":
        # Manual update check
        from updater.update_manager import main as update_main
        update_main()

    elif args.mode == "version":
        # Show version information
        from app.version import get_full_version_info
        version_info = get_full_version_info()
        print(f"HET IT Control System v{version_info['version']}")
        print(f"Build Date: {version_info['build_date']}")
        print(f"Author: {version_info['author']}")

    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()