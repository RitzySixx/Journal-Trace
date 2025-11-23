@echo off
title Build Journal Trace EXE
cd /d "%~dp0"

echo =====================================
echo        Building Journal Trace Executable
echo =====================================
echo.

echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH!
    echo.
    echo Please install Python from:
    echo https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo Installing required dependencies...
pip install pyinstaller pywebview pywin32

if errorlevel 1 (
    echo ERROR: Failed to install dependencies!
    pause
    exit /b 1
)

echo Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist __pycache__ rmdir /s /q __pycache__
if exist *.spec del *.spec

echo.
echo =====================================
echo     Building Executable...
echo =====================================

echo Checking for icon file...
if not exist "journal.ico" (
    echo WARNING: journal.ico not found!
    echo Building without custom icon...
    set ICON_CMD=
) else (
    echo Found journal.ico - applying custom icon...
    set ICON_CMD=--icon "journal.ico"
)

echo Building JournalTrace executable with PyInstaller...
python -m PyInstaller --onefile --windowed --name "JournalTrace" %ICON_CMD% ^
--add-data "web;web" ^
--hidden-import="webview" ^
--hidden-import="webview.platforms.win32" ^
--hidden-import="webview.platforms.wince" ^
--hidden-import="json" ^
--hidden-import="threading" ^
--hidden-import="datetime" ^
--hidden-import="pathlib" ^
--hidden-import="re" ^
--hidden-import="csv" ^
--hidden-import="ctypes" ^
--hidden-import="ctypes.wintypes" ^
--hidden-import="string" ^
--hidden-import="win32api" ^
--hidden-import="win32file" ^
--hidden-import="win32con" ^
--hidden-import="pywintypes" ^
--hidden-import="win32timezone" ^
--collect-all="webview" ^
--collect-all="pywin32" ^
JournalTrace.py

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    echo Please check the error messages above.
    pause
    exit /b 1
)

if exist dist\JournalTrace.exe (
    echo.
    echo =====================================
    echo      BUILD SUCCESSFUL!
    echo =====================================
    echo.
    echo Executable created: dist\JournalTrace.exe
    echo File size: 
    for %%F in (dist\JournalTrace.exe) do echo   %%~zF bytes
    echo.
    echo Journal Trace Features:
    echo - USN Journal parsing for Windows file system
    echo - Automatic scanning of all available NTFS drives
    echo - Comprehensive file operation tracking
    echo - Export to CSV functionality
    echo - Beautiful glass-morphism UI
    echo - Real-time progress monitoring
    echo.
    echo IMPORTANT: Run as Administrator for full functionality!
    echo.
    echo The executable is completely standalone!
    echo No Python or dependencies required to run.
    echo.
    echo You can now distribute dist\JournalTrace.exe
    echo.
    echo Build process completed.
    pause
)