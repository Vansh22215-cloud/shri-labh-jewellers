@echo off
cd /d "%~dp0\.."
".venv\Scripts\python.exe" scripts\run_weekly.py >> logs\weekly_console.log 2>&1
