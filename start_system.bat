@echo off
setlocal enabledelayedexpansion
title AI-Based Emergency Intelligence and Response System Using YOLO
color 0B

echo.
echo ====================================================================
echo   AI-BASED EMERGENCY INTELLIGENCE AND RESPONSE SYSTEM USING YOLO
echo   Emergency Operations Command Center (EOCC) - Local Launcher
echo ====================================================================
echo.

:: 1. Check Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] Python is not found in your system PATH.
    echo Please install Python 3.10+ from https://www.python.org/
    echo and ensure "Add Python to PATH" is checked during installation.
    echo.
    pause
    exit /b 1
)

:: 2. Check and activate virtual environment if present
if exist ".venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment (.venv)...
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment (venv)...
    call venv\Scripts\activate.bat
) else if exist "backend\venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment (backend\venv)...
    call backend\venv\Scripts\activate.bat
)

:: 3. Change directory to project root
cd /d "%~dp0"

:: 4. Verify YOLO model file
if exist "backend\models\yolov8n.pt" (
    echo [INFO] YOLOv8 nano model verified (backend\models\yolov8n.pt).
) else (
    echo [WARN] Model weights not found in backend\models\. Ultralytics will auto-download on first run.
)

:: 5. Display Localhost Access Links
echo.
echo --------------------------------------------------------------------
echo   LOCAL ACCESS INFORMATION:
echo   - EOCC Dashboard:  http://localhost:5000
echo   - Health Check:    http://localhost:5000/api/health
echo   - Live MJPEG Feed: http://localhost:5000/api/stream
echo --------------------------------------------------------------------
echo.
echo [INFO] Opening EOCC Dashboard in your default browser in 2 seconds...
echo [INFO] Starting Flask backend server (Press Ctrl+C to terminate)...
echo.

:: 6. Launch browser after a brief delay so server has time to bind
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:5000"

:: 7. Start Flask backend application
python backend\app.py

echo.
echo [INFO] Server stopped.
pause
