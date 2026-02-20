# scripts/build_exe.py
"""
Build script for creating HET IT Control System executable.
Uses PyInstaller to create a single EXE file.
"""

import subprocess
import sys
import os
from pathlib import Path
import shutil
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_command(cmd, cwd=None):
    """Run a command and return success status."""
    try:
        logger.info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        return False, e.stderr

def build_executable():
    """Build the executable using PyInstaller."""
    project_root = Path(__file__).parent.parent

    # Check if PyInstaller is installed
    try:
        import PyInstaller
        logger.info("PyInstaller is available")
    except ImportError:
        logger.error("PyInstaller not found. Install with: pip install pyinstaller")
        return False

    # Check if spec file exists
    spec_file = project_root / "build_exe.spec"
    if not spec_file.exists():
        logger.error(f"Spec file not found: {spec_file}")
        return False

    # Clean previous build
    dist_dir = project_root / "dist"
    build_dir = project_root / "build"

    if dist_dir.exists():
        logger.info("Cleaning previous dist directory")
        shutil.rmtree(dist_dir)

    if build_dir.exists():
        logger.info("Cleaning previous build directory")
        shutil.rmtree(build_dir)

    # Run PyInstaller
    cmd = [sys.executable, "-m", "PyInstaller", "--clean", str(spec_file)]
    success, output = run_command(cmd, cwd=project_root)

    if success:
        logger.info("PyInstaller build completed successfully")

        # Check if executable was created
        exe_path = dist_dir / "HET-IT-Control-System.exe"
        if exe_path.exists():
            exe_size = exe_path.stat().st_size / (1024 * 1024)  # Size in MB
            logger.info(".2f")
            return True
        else:
            logger.error("Executable not found after build")
            return False
    else:
        logger.error("PyInstaller build failed")
        return False

def create_installer():
    """Create a simple installer script."""
    project_root = Path(__file__).parent.parent
    dist_dir = project_root / "dist"
    exe_path = dist_dir / "HET-IT-Control-System.exe"

    if not exe_path.exists():
        logger.error("Executable not found. Build first.")
        return False

    # Create install script
    install_script = dist_dir / "install_service.bat"
    install_content = f'''@echo off
echo Installing HET IT Control System Service...
echo.

REM Copy executable to Program Files
set "INSTALL_DIR=%ProgramFiles%\\HET IT Control System"
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
copy "{exe_path}" "%INSTALL_DIR%\\HET-IT-Control-System.exe"

REM Install service
"%INSTALL_DIR%\\HET-IT-Control-System.exe" --startup auto install

REM Start service
"%INSTALL_DIR%\\HET-IT-Control-System.exe" start

echo.
echo Installation completed!
echo Service is now running and will start automatically on boot.
echo.
pause
'''

    try:
        with open(install_script, 'w') as f:
            f.write(install_content)
        logger.info(f"Created installer script: {install_script}")
        return True
    except Exception as e:
        logger.error(f"Failed to create installer: {e}")
        return False

def main():
    """Main build process."""
    logger.info("Starting HET IT Control System build process")

    # Build executable
    if not build_executable():
        logger.error("Build failed")
        return 1

    # Create installer
    if not create_installer():
        logger.warning("Failed to create installer, but build succeeded")

    logger.info("Build process completed successfully")
    logger.info("Find the executable and installer in the 'dist' directory")

    return 0

if __name__ == "__main__":
    sys.exit(main())
<parameter name="filePath">d:\My App\scripts\build_exe.py