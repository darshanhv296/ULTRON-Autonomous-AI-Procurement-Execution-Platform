@echo off
setlocal
title ULTRON - Local Launcher
cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
  echo Python 3.10+ is required. Install it from https://www.python.org/downloads/
  pause
  exit /b 1
)

if not exist "venv\Scripts\python.exe" (
  echo Creating virtual environment...
  python -m venv venv
  if errorlevel 1 goto :error
)

call "venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 goto :error
python -m pip install -r requirements.txt
if errorlevel 1 goto :error

if not exist ".env" (
  copy ".env.example" ".env" >nul
  echo Created .env. Add your optional integration credentials before using live integrations.
)

echo Starting ULTRON at http://127.0.0.1:8000
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
goto :eof

:error
echo Setup failed. Review the error above.
pause
exit /b 1
