@echo off
REM HET IT Control System - Build Script
REM Creates executable using PyInstaller

echo HET IT Control System - Build Script
echo ====================================

set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
set BUILD_DIR=%PROJECT_ROOT%\build
set DIST_DIR=%PROJECT_ROOT%\dist

echo Project Root: %PROJECT_ROOT%
echo Build Directory: %BUILD_DIR%
echo Distribution Directory: %DIST_DIR%
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not available in PATH
    echo Please ensure Python is installed and in your PATH
    pause
    exit /b 1
)

REM Check if PyInstaller is installed
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo ERROR: Failed to install PyInstaller
        pause
        exit /b 1
    )
)

REM Clean previous builds
echo Cleaning previous builds...
if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"

REM Create directories
if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"
if not exist "%DIST_DIR%" mkdir "%DIST_DIR%"

REM Build the executable
echo Building executable...
cd "%PROJECT_ROOT%"
python -m PyInstaller --clean --noconfirm packaging\het_control_system.spec

if errorlevel 1 (
    echo ERROR: Build failed
    pause
    exit /b 1
)

echo.
echo Build completed successfully!
echo Executable created at: %DIST_DIR%\HET_IT_Control_System\HET_IT_Control_System.exe
echo.

REM Create portable package
echo Creating portable package...
set PORTABLE_DIR=%DIST_DIR%\HET_IT_Control_System_Portable
if exist "%PORTABLE_DIR%" rmdir /s /q "%PORTABLE_DIR%"
mkdir "%PORTABLE_DIR%"

REM Copy executable and files
xcopy "%DIST_DIR%\HET_IT_Control_System\*" "%PORTABLE_DIR%\" /E /I /H /Y

REM Create batch files for easy launching
echo @echo off > "%PORTABLE_DIR%\Run_GUI.bat"
echo REM HET IT Control System - GUI Launcher >> "%PORTABLE_DIR%\Run_GUI.bat"
echo cd /d "%%~dp0" >> "%PORTABLE_DIR%\Run_GUI.bat"
echo HET_IT_Control_System.exe gui >> "%PORTABLE_DIR%\Run_GUI.bat"

echo @echo off > "%PORTABLE_DIR%\Run_Service.bat"
echo REM HET IT Control System - Service Launcher >> "%PORTABLE_DIR%\Run_Service.bat"
echo cd /d "%%~dp0" >> "%PORTABLE_DIR%\Run_Service.bat"
echo HET_IT_Control_System.exe scheduler >> "%PORTABLE_DIR%\Run_Service.bat"

echo @echo off > "%PORTABLE_DIR%\Run_Setup.bat"
echo REM HET IT Control System - Setup Wizard >> "%PORTABLE_DIR%\Run_Setup.bat"
echo cd /d "%%~dp0" >> "%PORTABLE_DIR%\Run_Setup.bat"
echo HET_IT_Control_System.exe setup >> "%PORTABLE_DIR%\Run_Setup.bat"

echo @echo off > "%PORTABLE_DIR%\Install_Service.bat"
echo REM HET IT Control System - Service Installer >> "%PORTABLE_DIR%\Install_Service.bat"
echo cd /d "%%~dp0" >> "%PORTABLE_DIR%\Install_Service.bat"
echo HET_IT_Control_System.exe service install >> "%PORTABLE_DIR%\Install_Service.bat"

echo.
echo Portable package created at: %PORTABLE_DIR%
echo.
echo Included batch files:
echo   Run_GUI.bat - Start GUI application
echo   Run_Service.bat - Start scheduler service
echo   Run_Setup.bat - Run setup wizard
echo   Install_Service.bat - Install Windows service
echo.

echo Build process completed!
echo You can now distribute the portable package.
echo.

pause