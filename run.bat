@echo off
setlocal

REM Always run from this script's directory.
cd /d "%~dp0"

if not exist ".venv\Scripts\Activate.ps1" (
    echo [ERROR] .venv is missing.
    echo Create and prepare it with:
    echo   python -m venv .venv
    echo   .\.venv\Scripts\Activate.ps1
    echo   python -m pip install -r requirements.txt
    pause
    exit /b 1
)

powershell -NoExit -ExecutionPolicy Bypass -Command "Set-Location '%~dp0'; . .\.venv\Scripts\Activate.ps1"
