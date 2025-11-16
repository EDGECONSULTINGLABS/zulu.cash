@echo off
git commit -m "Deploy ZULU landing page"
git push
echo.
echo ================================
echo ZULU.cash Deployment Complete!
echo ================================
echo.
echo Next steps:
echo 1. Go to: https://github.com/EDGECONSULTINGLABS/zulu.cash/settings/pages
echo 2. Under "Source", select "Deploy from a branch"
echo 3. Select "main" branch and "/" (root) folder
echo 4. Click Save
echo 5. Your site will be live at: https://edgeconsultinglabs.github.io/zulu.cash
echo.
pause
