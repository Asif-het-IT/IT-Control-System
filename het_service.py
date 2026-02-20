#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HET IT Control System - Service Bootstrap
Production-ready Windows service entry point.
"""

import sys
import os
from pathlib import Path

# Ensure we're in the correct directory
if getattr(sys, 'frozen', False):
    # Running as PyInstaller bundle
    application_path = Path(sys.executable).parent
else:
    # Running as script
    application_path = Path(__file__).parent

# Add application path to Python path
if str(application_path) not in sys.path:
    sys.path.insert(0, str(application_path))

# Import and run service
from app.service.windows_service import main

if __name__ == '__main__':
    main()