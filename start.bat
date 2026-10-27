@echo off
title Campus RAG System

set VENV_PYTHON=C:\Users\20122\PyCharmMiscProject\.venv\Scripts\python.exe
set ROOT=%~dp0

echo ========================================
echo   Campus Notification QnA System
echo ========================================
echo.

echo [1/4] Installing backend dependencies...
cd /d "%ROOT%backend"
"%VENV_PYTHON%" -m pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo Failed to install dependencies
    pause
    exit /b 1
)

echo [2/4] Initializing database...
"%VENV_PYTHON%" seed.py
if %errorlevel% neq 0 (
    echo Failed to initialize database
    pause
    exit /b 1
)

echo [3/4] Starting backend on port 8000...
start "Backend" "%ROOT%run_backend.bat"

echo [4/4] Starting frontend on port 3000...
cd /d "%ROOT%frontend"
call npm install --silent 2>nul
start "Frontend" "%ROOT%run_frontend.bat"

cd /d "%ROOT%"

echo.
echo ========================================
echo   System started successfully!
echo   Backend API : http://localhost:8000/docs
echo   Frontend    : http://localhost:3000
echo.
echo   Default accounts:
echo     Admin   : admin / admin123
echo     Student : student / student123
echo ========================================
echo.
echo Press any key to close this window...
pause >nul
