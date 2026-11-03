@echo off
cd /d "%~dp0\.."
start "" /B ".venv\Scripts\pythonw.exe" scripts\run_bot.py
