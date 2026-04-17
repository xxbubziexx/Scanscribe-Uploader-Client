@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
  echo Python was not found in PATH.
  echo Install Python 3 from https://www.python.org/downloads/ and enable "Add python.exe to PATH".
  exit /b 1
)

if not exist ".venv\" (
  echo Creating virtual environment .venv ...
  python -m venv .venv
  if errorlevel 1 exit /b 1
) else (
  echo Using existing .venv
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 exit /b 1

echo.
echo Done. In this window the venv is active. Next:
echo   python scanscribe_client_console.py --setup
echo   python scanscribe_client_console.py
echo.
echo In a new Command Prompt: cd to this folder, then run .venv\Scripts\activate.bat
echo.
pause
