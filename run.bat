@echo off
title Hackathon Project Launcher
echo =====================================
echo        Hackathon Project Launcher
echo =====================================
echo.

REM -------------------------------
REM Check if Python is installed
REM -------------------------------
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not added to PATH.
    echo.
    echo Please install Python 3.10 or higher from:
    echo https://www.python.org/downloads/windows/
    echo.
    echo IMPORTANT: Check "Add Python to PATH" during installation.
    pause
    exit /b
)

REM -------------------------------
REM Create virtual environment
REM -------------------------------
if not exist venv (
    echo 🔧 Creating virtual environment...
    python -m venv venv
)

REM -------------------------------
REM Activate virtual environment
REM -------------------------------
call venv\Scripts\activate

REM -------------------------------
REM Upgrade pip (safe & helpful)
REM -------------------------------
python -m pip install --upgrade pip >nul

REM -------------------------------
REM Install dependencies
REM -------------------------------
echo 📦 Installing dependencies...
python -m pip install -r requirements.txt

REM -------------------------------
REM Run the application
REM -------------------------------
echo.
echo 🚀 Application is starting...
echo 🌐 Open your browser at:
echo     http://127.0.0.1:5000
echo.
echo (Do not close this window while the app is running)
echo.

python Apple.py

pause
