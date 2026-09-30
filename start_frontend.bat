@echo off
set "PATH=C:\Users\anian\nodejs;%PATH%"
cd /d "%~dp0frontend"
echo Starting Galaxy Diagnostic Frontend on http://localhost:5173...
call npm run dev
pause
