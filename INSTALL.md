# Installation Guide for HET IT Control System

## Overview

This guide provides step-by-step instructions for installing the HET IT Control System on Windows 11 machines. The system is designed for automated IT monitoring and control without requiring central infrastructure.

## Prerequisites

### System Requirements
- Windows 11 (64-bit)
- Administrator privileges
- 500MB free disk space
- Network connectivity

### Required Software
- None (all dependencies are embedded in the executable)

## Installation Methods

### Method 1: Automated Installation (Recommended)

1. **Download the Installation Package**
   - Obtain `HET-IT-Control-System.exe` and `install_service.bat`
   - Place both files in the same directory

2. **Run Installation as Administrator**
   ```
   Right-click on install_service.bat
   Select "Run as administrator"
   ```

3. **Monitor Installation Progress**
   - The script will:
     - Copy the executable to Program Files
     - Install the Windows service
     - Start the service automatically
     - Set up auto-start on boot

4. **Verify Installation**
   - Open Windows Services (services.msc)
   - Look for "HET IT Control System" service
   - Status should be "Running"

### Method 2: Manual Installation

1. **Create Installation Directory**
   ```cmd
   mkdir "C:\Program Files\HET IT Control System"
   ```

2. **Copy Executable**
   ```cmd
   copy HET-IT-Control-System.exe "C:\Program Files\HET IT Control System\"
   ```

3. **Install Windows Service**
   ```cmd
   cd "C:\Program Files\HET IT Control System"
   HET-IT-Control-System.exe --startup auto install
   ```

4. **Start Service**
   ```cmd
   HET-IT-Control-System.exe start
   ```

## Post-Installation Configuration

### Launch the GUI
- Locate "HET IT Control System" in Start Menu
- Or run: `"C:\Program Files\HET IT Control System\HET-IT-Control-System.exe" gui`

### Initial Setup Wizard
1. **Email Configuration**
   - Enter SMTP server details
   - Provide sender email credentials
   - Test email functionality

2. **Job Configuration**
   - Review default job schedules
   - Enable/disable specific monitoring jobs
   - Configure job parameters

3. **System Settings**
   - Set log file locations
   - Configure backup settings
   - Set up notification preferences

## Service Management

### Using Windows Services Console
1. Press `Win + R`, type `services.msc`
2. Locate "HET IT Control System"
3. Right-click for start/stop/restart options

### Using Command Line
```cmd
# Check status
sc query "HET-IT-Control-System"

# Start service
sc start "HET-IT-Control-System"

# Stop service
sc stop "HET-IT-Control-System"

# Restart service
sc stop "HET-IT-Control-System"
sc start "HET-IT-Control-System"
```

### Using the Management Script
```cmd
# From the installation directory
python scripts\service_manager.py status
python scripts\service_manager.py restart
```

## Verification Steps

### 1. Service Verification
- [ ] Service appears in Windows Services console
- [ ] Service status is "Running"
- [ ] Startup type is "Automatic"
- [ ] Service starts after system reboot

### 2. GUI Verification
- [ ] GUI launches without errors
- [ ] Job list displays available jobs
- [ ] System status shows current information
- [ ] Log viewer is accessible

### 3. Job Verification
- [ ] Jobs appear in the job list
- [ ] Job schedules are configured
- [ ] Test job execution manually
- [ ] Verify job results are logged

### 4. Logging Verification
- [ ] Log files created in `logs\` directory
- [ ] Service logs show startup messages
- [ ] GUI logs show interface activity
- [ ] No error messages in logs

## Troubleshooting Installation Issues

### Service Won't Install
**Error:** "Access denied" or service installation fails

**Solution:**
1. Ensure running as Administrator
2. Check antivirus software isn't blocking
3. Verify executable integrity
4. Try manual installation method

### Service Won't Start
**Error:** Service fails to start after installation

**Solution:**
1. Check Windows Event Viewer for details
2. Review service logs in `logs\service.log`
3. Verify all dependencies are included
4. Check file permissions on installation directory

### GUI Won't Launch
**Error:** Double-clicking executable shows console then closes

**Solution:**
1. Run from command line to see error messages
2. Check GUI logs in `logs\gui.log`
3. Verify PySide6 components are accessible
4. Try running as different user

### Jobs Not Executing
**Error:** Jobs appear configured but don't run

**Solution:**
1. Check job schedules in GUI
2. Verify service is running
3. Review job configuration parameters
4. Test manual job execution

## Uninstalling

### Automated Uninstall
```cmd
# From installation directory
HET-IT-Control-System.exe stop
HET-IT-Control-System.exe remove
```

### Manual Uninstall
1. Stop the service in Windows Services console
2. Delete the service: `sc delete "HET-IT-Control-System"`
3. Remove installation directory
4. Clean up Windows Credential Manager entries (optional)

## Advanced Configuration

### Custom Installation Location
```cmd
# Set custom install path
set INSTALL_DIR=C:\Custom\Path
install_service.bat
```

### Service Account Configuration
```cmd
# Change service to run under specific account
sc config "HET-IT-Control-System" obj= "DOMAIN\Username" password= "Password"
```

### Log File Configuration
Edit `config/settings.py` to change:
- Log file locations
- Log rotation settings
- Log levels

## Support

### Log File Locations
- Service logs: `C:\Program Files\HET IT Control System\logs\service.log`
- GUI logs: `C:\Program Files\HET IT Control System\logs\gui.log`
- Database: `C:\Program Files\HET IT Control System\database\het_control.db`

### Getting Help
1. Check log files for error messages
2. Review Windows Event Viewer
3. Test components individually
4. Contact support with log excerpts

## Version Information
- Version: 1.0.0
- Build Date: [Current Date]
- Compatible with: Windows 11
- Architecture: 64-bit</content>
<parameter name="filePath">d:\My App\INSTALL.md