; HET IT Control System - NSIS Installer Script
; This script creates a professional Windows installer

!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"

; General Configuration
Name "HET IT Control System"
OutFile "HET_IT_Control_System_Installer.exe"
Unicode True
InstallDir "$PROGRAMFILES\HET IT Control System"
InstallDirRegKey HKCU "Software\HETITControlSystem" ""
RequestExecutionLevel admin

; Modern UI Configuration
!define MUI_ABORTWARNING
!define MUI_ICON "..\assets\icon.ico"  ; Add icon if available
!define MUI_UNICON "..\assets\icon.ico"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP "..\assets\header.bmp"  ; Add header image if available
!define MUI_WELCOMEFINISHPAGE_BITMAP "..\assets\wizard.bmp"  ; Add wizard image if available

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\LICENSE.txt"  ; Add license file if available
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; Languages
!insertmacro MUI_LANGUAGE "English"

; Version Information
VIProductVersion "1.0.0.0"
VIAddVersionKey "ProductName" "HET IT Control System"
VIAddVersionKey "CompanyName" "HET IT"
VIAddVersionKey "FileVersion" "1.0.0.0"
VIAddVersionKey "ProductVersion" "1.0.0.0"
VIAddVersionKey "FileDescription" "Enterprise Automation Dashboard"

; Installer Sections
Section "HET IT Control System" SecApp
    SectionIn RO

    SetOutPath "$INSTDIR"

    ; Copy all application files
    DetailPrint "Installing application files..."
    File /r "..\dist\HET_IT_Control_System\*.*"

    ; Create desktop shortcut
    CreateShortCut "$DESKTOP\HET IT Control System.lnk" "$INSTDIR\het_launcher.exe" "" "$INSTDIR\het_launcher.exe" 0

    ; Create start menu entries
    CreateDirectory "$SMPROGRAMS\HET IT Control System"
    CreateShortCut "$SMPROGRAMS\HET IT Control System\HET IT Control System.lnk" "$INSTDIR\het_launcher.exe" "" "$INSTDIR\het_launcher.exe" 0
    CreateShortCut "$SMPROGRAMS\HET IT Control System\Setup Wizard.lnk" "$INSTDIR\het_launcher.exe" "setup" "$INSTDIR\het_launcher.exe" 0
    CreateShortCut "$SMPROGRAMS\HET IT Control System\Service Manager.lnk" "$INSTDIR\service_manager.bat" "" "$INSTDIR\service_manager.bat" 0
    CreateShortCut "$SMPROGRAMS\HET IT Control System\Uninstall.lnk" "$INSTDIR\Uninstall.exe" "" "$INSTDIR\Uninstall.exe" 0

    ; Store installation folder
    WriteRegStr HKCU "Software\HETITControlSystem" "" $INSTDIR

    ; Create uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\HETITControlSystem" "DisplayName" "HET IT Control System"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\HETITControlSystem" "UninstallString" "$INSTDIR\Uninstall.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\HETITControlSystem" "DisplayVersion" "1.0.0"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\HETITControlSystem" "Publisher" "HET IT"
    WriteRegDWord HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\HETITControlSystem" "NoModify" 1
    WriteRegDWord HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\HETITControlSystem" "NoRepair" 1

    ; Create data directories
    CreateDirectory "$APPDATA\HET IT Control System"
    CreateDirectory "$APPDATA\HET IT Control System\logs"
    CreateDirectory "$APPDATA\HET IT Control System\database"

SectionEnd

; Uninstaller Section
Section "Uninstall"

    ; Stop and uninstall service if running
    DetailPrint "Stopping Windows service..."
    nsExec::ExecToLog '"$INSTDIR\service_manager.bat" stop'
    nsExec::ExecToLog '"$INSTDIR\service_manager.bat" uninstall'

    ; Remove files
    DetailPrint "Removing application files..."
    Delete "$INSTDIR\Uninstall.exe"
    RMDir /r "$INSTDIR"

    ; Remove shortcuts
    Delete "$DESKTOP\HET IT Control System.lnk"
    RMDir /r "$SMPROGRAMS\HET IT Control System"

    ; Remove registry entries
    DeleteRegKey HKCU "Software\HETITControlSystem"
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\HETITControlSystem"

    ; Remove data directories (ask user)
    MessageBox MB_YESNO "Do you want to remove all application data and logs?" IDYES remove_data
    Goto end_uninstall

    remove_data:
    RMDir /r "$APPDATA\HET IT Control System"

    end_uninstall:

SectionEnd

; Installer Functions
Function .onInit
    ; Check if already installed
    ReadRegStr $R0 HKCU "Software\HETITControlSystem" ""
    ${If} $R0 != ""
        MessageBox MB_YESNO "HET IT Control System is already installed. Do you want to reinstall?" IDYES continue_install
        Abort
        continue_install:
    ${EndIf}
FunctionEnd

; Uninstaller Functions
Function un.onInit
    MessageBox MB_YESNO "Are you sure you want to completely remove HET IT Control System and all of its components?" IDYES continue_uninstall
    Abort
    continue_uninstall:
FunctionEnd