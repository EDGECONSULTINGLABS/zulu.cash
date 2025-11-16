@echo off
git commit -m "Fix: Remove non-existent @zcash/sdk dependency from package.json"
git push
echo.
echo ================================
echo Fix Pushed to GitHub!
echo ================================
echo.
echo Now run in your terminal:
echo   cd backend
echo   npm install
echo   npm run dev
echo.
pause
