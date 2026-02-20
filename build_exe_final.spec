# build_exe.spec
"""
PyInstaller specification file for HET IT Control System.
Creates a single executable with embedded Python runtime.
"""

# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

# Get the project root directory
project_root = Path(__file__).parent

# Add project to Python path
sys.path.insert(0, str(project_root))

block_cipher = None

# Define data files to include
data_files = [
    # Include config files
    ('config', 'config'),
]

# Define hidden imports
hidden_imports = [
    'win32serviceutil',
    'win32service',
    'win32event',
    'servicemanager',
    'win32api',
    'win32con',
    'win32security',
    'win32cred',
    'apscheduler',
    'apscheduler.schedulers.background',
    'apscheduler.jobstores.memory',
    'apscheduler.executors.asyncio',
    'PySide6',
    'PySide6.QtCore',
    'PySide6.QtWidgets',
    'PySide6.QtGui',
    'sqlite3',
    'json',
    'logging',
    'pathlib',
    'dataclasses',
    'enum',
    'typing',
    'datetime',
    'uuid',
    'shutil',
    'tempfile',
    'subprocess',
    'threading',
    'concurrent.futures',
    'keyring',
    'keyring.backends.Windows',
]

a = Analysis(
    ['het_service.py'],  # Main script
    pathex=[str(project_root)],
    binaries=[],
    datas=data_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='HET-IT-Control-System',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window for service
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)