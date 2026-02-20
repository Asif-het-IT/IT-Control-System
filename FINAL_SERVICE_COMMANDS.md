# FINAL WINDOWS SERVICE INSTALL COMMANDS

## Automated Installation (Recommended)

### Single Command Installation
```cmd
REM Run as Administrator
install_service.bat
```

### Manual Installation Steps
```cmd
REM 1. Create installation directory
mkdir "%ProgramFiles%\HET IT Control System"

REM 2. Copy executable
copy "HET-IT-Control-System.exe" "%ProgramFiles%\HET IT Control System\"

REM 3. Install service
"%ProgramFiles%\HET IT Control System\HET-IT-Control-System.exe" --startup auto install

REM 4. Start service
"%ProgramFiles%\HET IT Control System\HET-IT-Control-System.exe" start
```

## Service Management Commands

### Check Service Status
```cmd
sc query "HET-IT-Control-System"
```

### Start Service
```cmd
sc start "HET-IT-Control-System"
```

### Stop Service
```cmd
sc stop "HET-IT-Control-System"
```

### Restart Service
```cmd
sc stop "HET-IT-Control-System"
sc start "HET-IT-Control-System"
```

### Delete Service (Uninstall)
```cmd
sc stop "HET-IT-Control-System"
sc delete "HET-IT-Control-System"
```

## PowerShell Commands

### Install Service
```powershell
# Run as Administrator
$exePath = "$env:ProgramFiles\HET IT Control System\HET-IT-Control-System.exe"
& $exePath --startup auto install
& $exePath start
```

### Check Service
```powershell
Get-Service "HET-IT-Control-System"
```

### Service Control
```powershell
# Start
Start-Service "HET-IT-Control-System"

# Stop
Stop-Service "HET-IT-Control-System"

# Restart
Restart-Service "HET-IT-Control-System"

# Set to Auto-start
Set-Service "HET-IT-Control-System" -StartupType Automatic
```

## Troubleshooting Commands

### View Service Events
```cmd
eventvwr.msc
```
Navigate to: Windows Logs > System
Filter by Source: HET-IT-Control-System

### Check Service Permissions
```cmd
REM Service should run as SYSTEM
sc qc "HET-IT-Control-System"
```

### View Service Logs
```cmd
type "%ProgramFiles%\HET IT Control System\logs\het_service.log"
```

### Test Service Manually
```cmd
"%ProgramFiles%\HET IT Control System\HET-IT-Control-System.exe" debug
```

## Reboot Validation Commands

### Pre-Reboot Checks
```cmd
REM Check service is running
sc query "HET-IT-Control-System"

REM Check service startup type
sc qc "HET-IT-Control-System"

REM Note current log size
dir "%ProgramFiles%\HET IT Control System\logs\"
```

### Post-Reboot Checks
```cmd
REM Verify service started automatically
sc query "HET-IT-Control-System"

REM Check for new log entries
dir "%ProgramFiles%\HET IT Control System\logs\"

REM Check service is responding
sc interrogate "HET-IT-Control-System"
```

## Bulk Deployment Commands

### For Multiple Machines (PowerShell)
```powershell
# List of target computers
$computers = @("PC001", "PC002", "PC003", "PC004", "PC005")

foreach ($computer in $computers) {
    Write-Host "Installing on $computer..."

    # Copy files
    Copy-Item "\\server\share\HET-IT-Control-System.exe" "\\$computer\c$\temp\" -Force
    Copy-Item "\\server\share\install_service.bat" "\\$computer\c$\temp\" -Force

    # Run installation remotely
    Invoke-Command -ComputerName $computer -ScriptBlock {
        Start-Process "C:\temp\install_service.bat" -Wait -Verb RunAs
    }

    Write-Host "Installation completed on $computer"
}
```

## Silent Installation

### For MDT/SCCM Deployment
```cmd
REM Silent install for enterprise deployment
HET-IT-Control-System.exe --startup auto --silent install
HET-IT-Control-System.exe start
```

## Uninstall Commands

### Complete Uninstall
```cmd
REM Stop service
sc stop "HET-IT-Control-System"

REM Delete service
sc delete "HET-IT-Control-System"

REM Remove files
rmdir /s /q "%ProgramFiles%\HET IT Control System"

REM Clean credentials (manual step required)
REM Use Windows Credential Manager to remove HET-IT-Control-System entries
```</content>
<parameter name="filePath">d:\My App\FINAL_SERVICE_COMMANDS.md