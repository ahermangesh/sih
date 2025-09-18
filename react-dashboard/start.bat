@echo off
echo Starting Dolphin Dashboard...
echo.
echo Installing dependencies...
call npm install
echo.
echo Starting development server...
call npm start
echo.
echo Dashboard should open at http://localhost:3000
pause
