@echo off
git commit -m "Add development setup - backend and frontend scaffolding"
git push
echo.
echo ================================
echo Development Setup Pushed!
echo ================================
echo.
echo Next steps:
echo 1. cd backend
echo 2. npm install
echo 3. cp .env.example .env
echo 4. Edit .env with your credentials
echo 5. npm run dev
echo.
pause
