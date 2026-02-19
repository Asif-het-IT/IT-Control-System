@echo off
cd /d "%~dp0"
call .venv\Scripts\activate
python gui\gui_launcher.py
pause
