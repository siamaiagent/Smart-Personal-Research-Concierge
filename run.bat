@echo off
echo ================================================================================
echo   SMART PERSONAL RESEARCH CONCIERGE
echo   Multi-Agent Research System
echo ================================================================================
echo.

REM Check if API key is set
if "%GOOGLE_API_KEY%"=="" (
    echo ERROR: GOOGLE_API_KEY environment variable not set!
    echo.
    echo Please set your API key first:
    echo   set GOOGLE_API_KEY=your-key-here
    echo.
    echo Or create a .env file with:
    echo   GOOGLE_API_KEY=your-key-here
    echo.
    pause
    exit /b 1
)

echo Starting research pipeline...
echo.

cd src
python main.py

echo.
echo ================================================================================
echo   Research pipeline completed!
echo ================================================================================
pause
