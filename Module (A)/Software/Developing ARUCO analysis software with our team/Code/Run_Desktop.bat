@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Local Python environment not found.
    echo Follow the setup steps in README.md to create .venv and install dependencies.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" app.py
if errorlevel 1 (
    echo.
    echo Application failed. Review the error above and the setup steps in README.md.
    pause
)
endlocal
