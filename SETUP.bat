@echo off
echo ==========================================
echo   ShortReel Uploader - Setup
echo ==========================================
echo.
echo Installing Python dependencies...
pip install -r requirements.txt

echo.
echo Installing Playwright browsers...
playwright install chromium

echo.
echo ==========================================
echo   Setup Complete!
echo   You can now close this window and run START.bat
echo ==========================================
pause
