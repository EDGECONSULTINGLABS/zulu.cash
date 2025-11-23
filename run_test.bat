@echo off
echo.
echo ================================================
echo ZULU LOCAL TEST
echo ================================================
echo.

echo Checking Python...
python --version
if errorlevel 1 (
    echo ERROR: Python not found
    pause
    exit /b 1
)

echo.
echo Installing requirements...
pip install -q -r requirements.txt

echo.
echo Running pipeline test...
python scripts\test_pipeline.py %*

pause
