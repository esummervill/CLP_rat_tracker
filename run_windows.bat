@echo off
title CLP Rat Tracker
echo.
echo  =============================================
echo    CLP Rat Tracker - Conditioned Place Preference
echo  =============================================
echo.

cd /d "%~dp0"

:: ---- Check for Python ----
where python >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python is not installed on this computer.
    echo.
    echo  To install Python:
    echo    1. Go to https://www.python.org/downloads/
    echo    2. Download the latest Python 3 installer
    echo    3. Run the installer
    echo    4. CHECK THE BOX: "Add Python to PATH"  ^<-- IMPORTANT
    echo    5. Click "Install Now"
    echo    6. After install finishes, close and re-open this script
    echo.
    pause
    exit /b 1
)

echo  [OK] Python found.
python --version
echo.

:: ---- Create virtual environment if it doesn't exist ----
if not exist "venv\Scripts\python.exe" (
    echo  Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo  [ERROR] Could not create virtual environment.
        echo  Trying to install without one...
        goto :install_global
    )
    echo  [OK] Virtual environment created.
    echo.
)

:: ---- Activate virtual environment ----
call venv\Scripts\activate.bat

:: ---- Install/update dependencies ----
echo  Checking dependencies...
pip show opencv-python >nul 2>&1
if errorlevel 1 (
    echo  Installing required packages (this may take a minute)...
    echo.
    pip install --upgrade pip
    pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo  [ERROR] Failed to install packages.
        echo  Try running manually:
        echo    pip install -r requirements.txt
        echo.
        pause
        exit /b 1
    )
    echo.
    echo  [OK] All packages installed.
    echo.
)

:: ---- Launch the app ----
echo  Starting CLP Rat Tracker...
echo.
python main.py
if errorlevel 1 (
    echo.
    echo  [ERROR] The application encountered an error.
    echo.
    echo  Try these steps:
    echo    1. Run: pip install -r requirements.txt
    echo    2. Run: python main.py
    echo.
    pause
)
goto :eof

:install_global
pip show opencv-python >nul 2>&1
if errorlevel 1 (
    echo  Installing required packages globally...
    pip install -r requirements.txt
)
python main.py
if errorlevel 1 (
    echo.
    echo  [ERROR] The application encountered an error.
    pause
)
