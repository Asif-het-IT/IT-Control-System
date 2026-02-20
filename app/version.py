# HET IT Control System Version Information
# This file is automatically updated during build process

__version__ = "1.1.0"
__version_info__ = (1, 1, 0)
__build_date__ = "2026-02-20"
__author__ = "HET IT Control System"
__description__ = "Enterprise Automation Dashboard"

# Version history
VERSION_HISTORY = {
    "1.0.0": {
        "date": "2026-02-20",
        "changes": [
            "Initial professional release",
            "Windows service support",
            "PyInstaller packaging",
            "Setup wizard",
            "Monitoring and alerting system",
            "Enterprise-grade architecture"
        ]
    }
}

def get_version_string():
    """Get formatted version string."""
    return f"v{__version__} ({__build_date__})"

def get_full_version_info():
    """Get complete version information."""
    return {
        "version": __version__,
        "version_info": __version_info__,
        "build_date": __build_date__,
        "author": __author__,
        "description": __description__,
        "history": VERSION_HISTORY
    }