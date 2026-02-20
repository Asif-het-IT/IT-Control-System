# FINAL REBOOT VALIDATION CHECKLIST

## Pre-Reboot Preparation

### 1. Service Configuration
- [ ] Service is installed: `sc query "HET-IT-Control-System"`
- [ ] Startup type is Automatic: `sc qc "HET-IT-Control-System"`
- [ ] Service is currently running
- [ ] No pending service errors in Event Viewer

### 2. System State Capture
- [ ] Note current date/time: `echo %DATE% %TIME%`
- [ ] Record service PID: `tasklist /FI "SERVICES eq HET-IT-Control-System"`
- [ ] Check log file size: `dir "%ProgramFiles%\HET IT Control System\logs\"`
- [ ] Verify database file exists: `dir "%ProgramFiles%\HET IT Control System\database\"`

### 3. Network Configuration
- [ ] Network connectivity confirmed
- [ ] Firewall rules allow service communication
- [ ] DNS resolution working
- [ ] Proxy settings configured (if needed)

## Reboot Execution

### 1. Safe Reboot
- [ ] Close all user applications
- [ ] Save all work
- [ ] Initiate reboot: `shutdown /r /t 30`
- [ ] Wait for complete shutdown

### 2. Post-Reboot Verification (Within 5 minutes)

#### Service Auto-Start
- [ ] Login to Windows (any user or none)
- [ ] Check service status: `sc query "HET-IT-Control-System"`
- [ ] Verify status is "RUNNING"
- [ ] Confirm new PID is different from pre-reboot
- [ ] Check startup time in Event Viewer

#### Log File Validation
- [ ] New log entries created: `dir "%ProgramFiles%\HET IT Control System\logs\"`
- [ ] Service startup logged: `type "%ProgramFiles%\HET IT Control System\logs\het_service.log" | findstr "started"`
- [ ] No error messages in logs
- [ ] Log rotation working (if applicable)

#### Database Integrity
- [ ] Database file accessible: `dir "%ProgramFiles%\HET IT Control System\database\"`
- [ ] WAL mode active: Check for .db-wal file
- [ ] No database corruption errors in logs
- [ ] Backup creation working (if scheduled)

#### Scheduler Functionality
- [ ] Jobs are scheduled: Check scheduler logs
- [ ] Background tasks running
- [ ] No scheduler initialization errors
- [ ] Job execution working

## Extended Validation (30 minutes post-reboot)

### 1. Job Execution
- [ ] Scheduled jobs run at expected times
- [ ] Job results logged correctly
- [ ] Email notifications sent (if configured)
- [ ] File operations successful

### 2. Resource Usage
- [ ] CPU usage normal (< 5% sustained)
- [ ] Memory usage stable
- [ ] Disk I/O reasonable
- [ ] Network activity as expected

### 3. Error Monitoring
- [ ] No errors in Windows Event Viewer
- [ ] No exceptions in service logs
- [ ] No database connection issues
- [ ] No credential access problems

## Failure Recovery Procedures

### If Service Doesn't Start
1. [ ] Check Event Viewer for startup errors
2. [ ] Review service logs for details
3. [ ] Try manual start: `sc start "HET-IT-Control-System"`
4. [ ] Check service dependencies
5. [ ] Verify executable integrity

### If Service Starts But Jobs Fail
1. [ ] Check scheduler initialization in logs
2. [ ] Verify database connectivity
3. [ ] Test credential access
4. [ ] Check network permissions
5. [ ] Review job configuration

### If Database Issues
1. [ ] Check database file permissions
2. [ ] Verify WAL mode is enabled
3. [ ] Restore from backup if needed
4. [ ] Check for corruption: `sqlite3 het_control.db "PRAGMA integrity_check;"`
5. [ ] Reinitialize database if necessary

## Success Criteria

### All Must Pass
- [ ] Service starts automatically within 2 minutes of boot
- [ ] No errors in Windows Event Viewer
- [ ] Service logs show successful initialization
- [ ] Database is accessible and healthy
- [ ] Scheduler is running and jobs are active
- [ ] At least one job executes successfully within 30 minutes
- [ ] System resources remain stable
- [ ] No security or permission errors

### Performance Benchmarks
- [ ] Boot time increase < 30 seconds
- [ ] Service startup time < 10 seconds
- [ ] Memory usage < 100MB after startup
- [ ] CPU usage < 5% during normal operation

## Documentation

### Record Results
- [ ] Boot time: ____ minutes ____ seconds
- [ ] Service startup time: ____ seconds
- [ ] First job execution: ____ minutes after boot
- [ ] Any errors encountered: ____________________
- [ ] Resolution steps taken: ____________________
- [ ] Final status: PASS / FAIL

### Log Preservation
- [ ] Save pre-reboot logs for comparison
- [ ] Archive post-reboot logs
- [ ] Document any anomalies
- [ ] Update troubleshooting guides if needed

## Multiple Machine Validation

### For 20-Machine Deployment
- [ ] Test on representative sample (3-5 machines)
- [ ] Validate different hardware configurations
- [ ] Test various network conditions
- [ ] Verify domain vs workgroup scenarios
- [ ] Confirm user privilege variations

### Batch Validation Script
```powershell
# Run on each machine post-reboot
$serviceName = "HET-IT-Control-System"
$logPath = "$env:ProgramFiles\HET IT Control System\logs\het_service.log"

# Check service
$service = Get-Service $serviceName
if ($service.Status -eq "Running") {
    Write-Host "✓ Service is running"
} else {
    Write-Host "✗ Service not running"
}

# Check logs
if (Test-Path $logPath) {
    $lastWrite = (Get-Item $logPath).LastWriteTime
    $timeDiff = (Get-Date) - $lastWrite
    if ($timeDiff.TotalMinutes -lt 5) {
        Write-Host "✓ Logs are current"
    } else {
        Write-Host "✗ Logs are stale"
    }
} else {
    Write-Host "✗ Log file not found"
}
```</content>
<parameter name="filePath">d:\My App\FINAL_REBOOT_CHECKLIST.md