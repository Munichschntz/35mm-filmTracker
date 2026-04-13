@echo off
setlocal

REM Always run from this script's directory.
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Creating virtual environment at .venv ...
    python -m venv .venv
    if errorlevel 1 (
        py -3 -m venv .venv
    )
    if errorlevel 1 (
        echo [ERROR] Failed to create .venv. Install Python and retry.
        pause
        exit /b 1
    )
)

if not exist "requirements.txt" (
    echo [ERROR] requirements.txt not found in project root.
    pause
    exit /b 1
)

if not exist "film_tracker.py" (
    echo [ERROR] film_tracker.py not found in project root.
    pause
    exit /b 1
)

echo [INFO] Installing/updating dependencies in .venv ...
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies into .venv.
    pause
    exit /b 1
)

echo [INFO] Starting film_tracker.py ...
.\.venv\Scripts\python.exe .\film_tracker.py
exit /b %errorlevel%
