@echo off
echo ============================================
echo   ShortReel Uploader - First Time Setup
echo ============================================
echo.

echo [1/3] Installing Python dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: pip install failed. Make sure Python is installed.
    pause
    exit /b 1
)

echo.
echo [2/3] Installing Playwright browsers...
playwright install chromium
if %errorlevel% neq 0 (
    echo ERROR: Playwright browser install failed.
    pause
    exit /b 1
)

echo.
echo [3/3] Setup complete!
echo.
echo ============================================
echo  Run START.bat to launch the uploader
echo ============================================
pause
