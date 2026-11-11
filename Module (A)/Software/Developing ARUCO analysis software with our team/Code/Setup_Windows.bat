@echo off
setlocal
cd /d "%~dp0"
echo ArUco Studio Desktop - local Python 3.12 setup
if not exist ".venv\Scripts\python.exe" (
    py -3.12 -m venv .venv
    if errorlevel 1 goto fail
)
".venv\Scripts\python.exe" -c "import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else 1)"
if errorlevel 1 (
    echo This folder's .venv does not use Python 3.12.
    echo Rename the existing .venv folder and run this setup again.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m pip install --upgrade pip --index-url https://pypi.org/simple
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m pip install -r requirements.txt --index-url https://pypi.org/simple
if errorlevel 1 goto fail
echo.
echo Setup completed. Double-click Run_Desktop.bat to start the application.
pause
exit /b 0
:fail
echo.
echo Setup failed. Read the installation error above before running the application.
pause
exit /b 1
