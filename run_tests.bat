@echo off
title AI Emergency Intelligence - Test Suite
color 0A

echo.
echo ====================================================================
echo   RUNNING EMERGENCY INTELLIGENCE BACKEND TEST SUITE (10 TESTS)
echo ====================================================================
echo.

cd /d "%~dp0"

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else if exist "backend\venv\Scripts\activate.bat" (
    call backend\venv\Scripts\activate.bat
)

python backend\test_backend.py

echo.
echo [INFO] Test execution finished.
pause
