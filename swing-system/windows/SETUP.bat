@echo off
REM ============================================================
REM  ONE-TIME SETUP - double-click this file.
REM  Installs the needed Python packages, downloads data, runs the
REM  backtest, schedules the nightly + weekly jobs, opens the report.
REM ============================================================
cd /d "%~dp0\.."
echo.
echo  Swing system setup - this can take 1-3 hours the first time (it tests ~550 strategies).
echo  Keep this window open. You can use your PC normally meanwhile.
echo.
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
  echo  Python is not installed. Please follow Step 1 in README.md, then double-click SETUP.bat again.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" %PY% -m venv .venv
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo  Package installation failed - check your internet connection and run SETUP.bat again.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" scripts\first_setup.py
powershell -NoProfile -ExecutionPolicy Bypass -File "windows\install_tasks.ps1"
echo.
echo  DONE. Your first report will open now. From now on it updates every weekday evening.
start "" "reports\latest.html"
pause
