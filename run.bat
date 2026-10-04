@echo off
setlocal
title Malayalam Voice Studio
cd /d "%~dp0"
set "PYTHONUTF8=1"
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo Python environment is missing. Run scripts\setup.ps1 first.
    pause
    exit /b 1
)
"%~dp0.venv\Scripts\python.exe" "%~dp0app.py"
if errorlevel 1 (
    echo.
    echo Voice Studio could not start or encountered an error.
    echo Check the error above and the logs folder for details.
    pause
    exit /b 1
)
endlocal
