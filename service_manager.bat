@echo off
REM het IT Control System - Service Management Script
REM Usage: service_manager.bat [install|uninstall|start|stop|status]

setlocal enabledelayedexpansion

set SERVICE_NAME=het-service
set SERVICE_DISPLAY_NAME="het IT Control System"
set SERVICE_DESCRIPTION="Automated IT control and monitoring service"
set SCRIPT_DIR=%~dp0
set SERVICE_EXE=%SCRIPT_DIR%dist\het_service.exe

echo het IT Control System - Service Manager
echo ======================================

if "%1"=="install" goto install
if "%1"=="uninstall" goto uninstall
if "%1"=="start" goto start
if "%1"=="stop" goto stop
if "%1"=="status" goto status
if "%1"=="restart" goto restart

echo Usage: %0 [install^|uninstall^|start^|stop^|status^|restart]
echo.
echo Commands:
echo   install   - Install and start the service
echo   uninstall - Stop and uninstall the service
echo   start     - Start the service
echo   stop      - Stop the service
echo   status    - Show service status
echo   restart   - Restart the service
goto end

:install
echo Installing het IT Control System service...
"%SERVICE_EXE%" install
if errorlevel 1 (
    echo ERROR: Failed to install service
    goto end
)
echo Service installed successfully.
echo Starting service...
"%SERVICE_EXE%" start
if errorlevel 1 (
    echo ERROR: Failed to start service
    goto end
)
echo Service started successfully.
goto end

:uninstall
echo Stopping het IT Control System service...
"%SERVICE_EXE%" stop
echo Uninstalling service...
"%SERVICE_EXE%" remove
if errorlevel 1 (
    echo ERROR: Failed to uninstall service
    goto end
)
echo Service uninstalled successfully.
goto end

:start
echo Starting het IT Control System service...
"%SERVICE_EXE%" start
if errorlevel 1 (
    echo ERROR: Failed to start service
    goto end
)
echo Service started successfully.
goto end

:stop
echo Stopping het IT Control System service...
"%SERVICE_EXE%" stop
if errorlevel 1 (
    echo ERROR: Failed to stop service
    goto end
)
echo Service stopped successfully.
goto end

:status
echo Checking het IT Control System service status...
sc query "%SERVICE_NAME%" | findstr STATE
goto end

:restart
echo Restarting het IT Control System service...
"%SERVICE_EXE%" restart
if errorlevel 1 (
    echo ERROR: Failed to restart service
    goto end
)
echo Service restarted successfully.
goto end

:end
echo.
pause