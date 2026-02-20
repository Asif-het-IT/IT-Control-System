# Deployment Checklist for HET IT Control System

## Pre-Deployment Preparation

### 1. System Requirements Check
- [ ] Windows 11 (64-bit) operating system
- [ ] Administrator privileges available
- [ ] 500MB free disk space
- [ ] Network connectivity for initial setup
- [ ] Antivirus exclusions configured (if needed)

### 2. Build Verification
- [ ] PyInstaller executable built successfully
- [ ] `HET-IT-Control-System.exe` exists in `dist/` folder
- [ ] `install_service.bat` created
- [ ] All dependencies included in executable
- [ ] Test executable on clean Windows 11 VM

### 3. Configuration Preparation
- [ ] Email credentials configured in Windows Credential Manager
- [ ] Database credentials stored securely
- [ ] Job schedules reviewed and set appropriately
- [ ] Log rotation settings configured
- [ ] Backup schedule configured

## Deployment Steps

### Phase 1: Initial Installation (Per Machine)

1. **Copy Files**
   - [ ] Copy `HET-IT-Control-System.exe` to target machine
   - [ ] Copy `install_service.bat` to same directory
   - [ ] Ensure both files are in the same folder

2. **Run Installation as Administrator**
   - [ ] Right-click `install_service.bat`
   - [ ] Select "Run as administrator"
   - [ ] Verify service installation completes without errors
   - [ ] Check Windows Services console for "HET IT Control System" service

3. **Verify Service Startup**
   - [ ] Open Windows Services (services.msc)
   - [ ] Locate "HET IT Control System" service
   - [ ] Verify service status is "Running"
   - [ ] Check startup type is "Automatic"
   - [ ] Confirm service starts after system reboot

### Phase 2: Configuration Setup

1. **Credential Configuration**
   - [ ] Launch GUI application
   - [ ] Configure email settings (SMTP server, credentials)
   - [ ] Set up database connection details (if external)
   - [ ] Configure API keys for external services

2. **Job Configuration**
   - [ ] Review default job schedules
   - [ ] Adjust job frequencies based on requirements
   - [ ] Enable/disable specific jobs as needed
   - [ ] Configure job-specific parameters

3. **System Integration**
   - [ ] Set up automated email notifications
   - [ ] Configure log file locations
   - [ ] Set up backup destinations
   - [ ] Configure monitoring alerts

## Post-Deployment Verification

### Service Verification
- [ ] Service starts automatically on boot
- [ ] Service runs under correct user account
- [ ] Service has necessary network permissions
- [ ] Service can access required file shares

### Job Verification
- [ ] Jobs execute according to schedule
- [ ] Job results are logged correctly
- [ ] Email notifications are sent (if configured)
- [ ] Database records are created/updated

### GUI Verification
- [ ] GUI launches without errors
- [ ] Job status displays correctly
- [ ] Log viewer shows current activity
- [ ] System status information is accurate

### Monitoring Setup
- [ ] Log files are created and rotating properly
- [ ] Database backups are created automatically
- [ ] Error conditions trigger appropriate alerts
- [ ] Performance monitoring is functional

## Troubleshooting Checklist

### Service Issues
- [ ] Check Windows Event Viewer for service errors
- [ ] Verify executable path in service configuration
- [ ] Confirm administrator privileges
- [ ] Check antivirus blocking service
- [ ] Review service logs in `logs/service.log`

### Job Execution Issues
- [ ] Verify job schedules are active
- [ ] Check job configuration parameters
- [ ] Confirm network connectivity for external jobs
- [ ] Review job-specific error logs
- [ ] Test job execution manually via GUI

### Database Issues
- [ ] Verify database file permissions
- [ ] Check database file integrity
- [ ] Confirm WAL mode is enabled
- [ ] Review database connection logs
- [ ] Test database backup functionality

### GUI Issues
- [ ] Check GUI log files for errors
- [ ] Verify PySide6 components are accessible
- [ ] Confirm user has necessary permissions
- [ ] Test GUI on different user accounts

## Maintenance Schedule

### Daily Checks
- [ ] Verify service is running
- [ ] Check for new log entries
- [ ] Monitor disk space usage
- [ ] Review job execution status

### Weekly Tasks
- [ ] Review log files for errors
- [ ] Check database backup integrity
- [ ] Verify job schedules are current
- [ ] Update job configurations if needed

### Monthly Tasks
- [ ] Full system health check
- [ ] Review and clean old log files
- [ ] Update job parameters based on performance
- [ ] Verify backup retention policies

## Rollback Plan

### Emergency Stop
1. Open Windows Services console
2. Stop "HET IT Control System" service
3. Set startup type to "Disabled"
4. Delete service using command: `sc delete "HET-IT-Control-System"`

### Data Recovery
1. Restore from database backup
2. Reconfigure credentials in Windows Credential Manager
3. Reinstall service with fresh executable
4. Restore job configurations from backup

### Clean Uninstall
1. Stop and delete service
2. Remove installation directory
3. Clean Windows Credential Manager entries
4. Remove any scheduled tasks (if created)
5. Delete log files and database (optional)

## Support Information

### Log File Locations
- Service logs: `%ProgramFiles%\HET IT Control System\logs\service.log`
- GUI logs: `%ProgramFiles%\HET IT Control System\logs\gui.log`
- Database: `%ProgramFiles%\HET IT Control System\database\het_control.db`

### Contact Information
- Development Team: [contact information]
- Emergency Support: [emergency contact]
- Documentation: [link to full documentation]

### Version Information
- Current Version: 1.0.0
- Build Date: [build date]
- Python Version: 3.11
- PyInstaller Version: [version used]</content>
<parameter name="filePath">d:\My App\DEPLOYMENT_CHECKLIST.md