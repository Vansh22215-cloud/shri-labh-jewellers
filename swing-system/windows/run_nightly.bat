@echo off
cd /d "%~dp0\.."
".venv\Scripts\python.exe" scripts\run_nightly.py >> logs\nightly_console.log 2>&1
start "" "reports\latest.html"
