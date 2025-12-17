@echo off
REM Zulu Verification System - Installation Script (Windows)

echo.
echo Zulu Verification System - Installation
echo ==========================================
echo.

REM Check Node.js
where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Node.js is not installed
    echo Please install Node.js 18+ from https://nodejs.org/
    exit /b 1
)

for /f "tokens=1" %%i in ('node -v') do set NODE_VERSION=%%i
echo [OK] Node.js %NODE_VERSION% detected
echo.

REM Install dependencies
echo [INSTALL] Installing dependencies...
call npm install
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Dependency installation failed
    exit /b 1
)
echo [OK] Dependencies installed
echo.

REM Build TypeScript
echo [BUILD] Building TypeScript...
call npm run build
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Build failed
    exit /b 1
)
echo [OK] Build complete
echo.

REM Run tests
echo [TEST] Running tests...
call npm test
if %ERRORLEVEL% NEQ 0 (
    echo [WARN] Some tests failed, but installation is complete
    echo Review test output above
) else (
    echo [OK] All tests passed
)

echo.
echo [SUCCESS] Installation complete!
echo.
echo Next steps:
echo   1. Review QUICKSTART.md for usage guide
echo   2. Run examples: node dist\examples\basic-usage.js
echo   3. Run benchmarks: npm run benchmark
echo   4. Set environment variable: set ZULU_DB_KEY=your-key
echo.
echo Ready to secure Zulu's artifact distribution!
