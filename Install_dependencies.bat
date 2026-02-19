@echo off
REM =====================================================
REM (het) Automation Dashboard – FULL ONE-CLICK INSTALLER
REM Fresh Windows | Python 3.13 / 3.14 Compatible
REM Author: Asif Ali
REM =====================================================

echo.
echo ==== STEP 0: Check Python Installation ====
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Python not found! Please install Python 3.13/3.14 first.
    pause
    exit /b
)

echo.
echo ==== STEP 1: Upgrade pip & base tools ====
python -m ensurepip --upgrade
python -m pip install --upgrade pip setuptools wheel

echo.
echo ==== STEP 2: Install Dependencies from requirements.txt ====
SET REQ_FILE=D:\01 - SSS 300 LAUNDRY - Exports To Excel\requirements.txt
IF NOT EXIST "%REQ_FILE%" (
    echo requirements.txt not found at %REQ_FILE%
    pause
    exit /b
)

python -m pip install -r "%REQ_FILE%"

echo.
echo ==== STEP 3: Verify All Modules ====
python - <<EOF
errors = []

modules = [
    "customtkinter",
    "Pillow",
    "paramiko",
    "pysmb",
    "requests",
    "openpyxl",
    "pandas",
    "pytz",
    "python_dateutil",
    "psutil",
    "speedtest",
    "matplotlib",
    "pyperclip",
    "yagmail",
    "keyring"
]

for m in modules:
    try:
        if m=="speedtest":
            from speedtest import Speedtest
        else:
            __import__(m)
    except Exception:
        errors.append(m)

if errors:
    print("MISSING MODULES:", ", ".join(errors))
else:
    print("ALL DEPENDENCIES INSTALLED SUCCESSFULLY ✅")
EOF

echo.
echo ==== INSTALLATION COMPLETE ====
pause
