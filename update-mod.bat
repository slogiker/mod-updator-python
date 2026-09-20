@echo off
setlocal enabledelayedexpansion

:: ============================================================================
:: update-mod.bat - Windows Launcher for Minecraft Mod Updater
:: ============================================================================

title Minecraft Mod Updater

:: Navigate to script directory
cd /d "%~dp0"

:: 1. Detect Python
set "PY_CMD="

where py >nul 2>nul
if %errorlevel% equ 0 (
    set "PY_CMD=py -3"
) else (
    where python >nul 2>nul
    if %errorlevel% equ 0 (
        set "PY_CMD=python"
    ) else (
        where python3 >nul 2>nul
        if %errorlevel% equ 0 (
            set "PY_CMD=python3"
        )
    )
)

if "%PY_CMD%"=="" (
    echo.
    echo ================================================================
    echo [ERROR] Python was not detected on your system!
    echo ================================================================
    echo Please install Python 3.9 or newer from:
    echo https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: 2. Check for virtual environment or dependencies
if exist ".venv\Scripts\python.exe" (
    set "PY_CMD=.venv\Scripts\python.exe"
) else (
    %PY_CMD% -c "import requests" >nul 2>nul
    if %errorlevel% neq 0 (
        echo [INFO] Installing required libraries (requests)...
        %PY_CMD% -m pip install -r requirements.txt
        if %errorlevel% neq 0 (
            echo.
            echo [ERROR] Failed to install dependencies.
            pause
            exit /b 1
        )
    )
)

:: 3. Run updater
set "PYTHONPATH=%~dp0;%PYTHONPATH%"
%PY_CMD% -m mod_updater.cli %*
set "EXIT_CODE=%errorlevel%"

:: If run by double clicking (no arguments supplied), keep window open
if "%~1"=="" (
    echo.
    pause
)

exit /b %EXIT_CODE%
