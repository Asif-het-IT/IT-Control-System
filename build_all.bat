@echo off
REM HET IT Control System - Complete Build Script
REM Builds executable, creates portable package, and installer

echo ========================================
echo HET IT Control System - Complete Build
echo ========================================
echo.

set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
set BUILD_DIR=%PROJECT_ROOT%\build
set DIST_DIR=%PROJECT_ROOT%\dist

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not available in PATH
    echo Please ensure Python is installed and in your PATH
    pause
    exit /b 1
)

echo [1/6] Installing build dependencies...
pip install pyinstaller pywin32 --quiet
if errorlevel 1 (
    echo ERROR: Failed to install build dependencies
    pause
    exit /b 1
)

echo.
echo [2/6] Updating version information...
python -c "
from datetime import datetime
import re

# Update version file with build date
with open('app/version.py', 'r') as f:
    content = f.read()

content = re.sub(r'__build_date__ = \".*\"', f'__build_date__ = \"{datetime.now().strftime(\"%Y-%m-%d\")}\"', content)

with open('app/version.py', 'w') as f:
    f.write(content)

print('Version information updated')
"

echo.
echo [3/6] Building executable with PyInstaller...
cd "%PROJECT_ROOT%\packaging"
call build.bat
if errorlevel 1 (
    echo ERROR: Executable build failed
    pause
    exit /b 1
)

echo.
echo [4/6] Creating portable package...
if not exist "%DIST_DIR%\HET_IT_Control_System_Portable" mkdir "%DIST_DIR%\HET_IT_Control_System_Portable"

REM Copy executable and create launcher scripts
xcopy "%DIST_DIR%\HET_IT_Control_System\*" "%DIST_DIR%\HET_IT_Control_System_Portable\" /E /I /H /Y

echo @echo off > "%DIST_DIR%\HET_IT_Control_System_Portable\Run_GUI.bat"
echo REM HET IT Control System - GUI Launcher >> "%DIST_DIR%\HET_IT_Control_System_Portable\Run_GUI.bat"
echo cd /d "%%~dp0" >> "%DIST_DIR%\HET_IT_Control_System_Portable\Run_GUI.bat"
echo het_launcher.exe gui >> "%DIST_DIR%\HET_IT_Control_System_Portable\Run_GUI.bat"

echo @echo off > "%DIST_DIR%\HET_IT_Control_System_Portable\Run_Setup.bat"
echo REM HET IT Control System - Setup Wizard >> "%DIST_DIR%\HET_IT_Control_System_Portable\Run_Setup.bat"
echo cd /d "%%~dp0" >> "%DIST_DIR%\HET_IT_Control_System_Portable\Run_Setup.bat"
echo het_launcher.exe setup >> "%DIST_DIR%\HET_IT_Control_System_Portable\Run_Setup.bat"

echo @echo off > "%DIST_DIR%\HET_IT_Control_System_Portable\Service_Install.bat"
echo REM HET IT Control System - Service Installer >> "%DIST_DIR%\HET_IT_Control_System_Portable\Service_Install.bat"
echo cd /d "%%~dp0" >> "%DIST_DIR%\HET_IT_Control_System_Portable\Service_Install.bat"
echo het_launcher.exe service install >> "%DIST_DIR%\HET_IT_Control_System_Portable\Service_Install.bat"

echo @echo off > "%DIST_DIR%\HET_IT_Control_System_Portable\Service_Uninstall.bat"
echo REM HET IT Control System - Service Uninstaller >> "%DIST_DIR%\HET_IT_Control_System_Portable\Service_Uninstall.bat"
echo cd /d "%%~dp0" >> "%DIST_DIR%\HET_IT_Control_System_Portable\Service_Uninstall.bat"
echo het_launcher.exe service uninstall >> "%DIST_DIR%\HET_IT_Control_System_Portable\Service_Uninstall.bat"

echo.
echo [5/6] Creating installer package...
if exist "C:\Program Files (x86)\NSIS\makensis.exe" (
    echo Building NSIS installer...
    "C:\Program Files (x86)\NSIS\makensis.exe" installer.nsi
    if exist "HET_IT_Control_System_Installer.exe" (
        move "HET_IT_Control_System_Installer.exe" "%DIST_DIR%\"
        echo Installer created: %DIST_DIR%\HET_IT_Control_System_Installer.exe
    ) else (
        echo WARNING: NSIS installer creation failed - NSIS not found
        echo Portable package still available
    )
) else (
    echo WARNING: NSIS not found - skipping installer creation
    echo Install NSIS from https://nsis.sourceforge.io/ for installer creation
)

echo.
echo [6/6] Creating distribution archive...
cd "%DIST_DIR%"
if exist "HET_IT_Control_System_Distribution.zip" del "HET_IT_Control_System_Distribution.zip"
powershell "Compress-Archive -Path 'HET_IT_Control_System_Portable' -DestinationPath 'HET_IT_Control_System_Distribution.zip' -Force"

echo.
echo ========================================
echo BUILD COMPLETED SUCCESSFULLY!
echo ========================================
echo.
echo Distribution files created in: %DIST_DIR%
echo.
echo Files available:
echo • HET_IT_Control_System_Portable\          (Portable version)
echo • HET_IT_Control_System_Distribution.zip   (Zipped portable)
if exist "HET_IT_Control_System_Installer.exe" (
    echo • HET_IT_Control_System_Installer.exe      (Windows installer)
)
echo.
echo To distribute:
echo 1. Use the installer for professional deployment
echo 2. Use the portable version for quick testing
echo 3. Use the zip file for web distribution
echo.
echo Installation instructions in README.md
echo.

pause