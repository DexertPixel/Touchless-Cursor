@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating a private Python environment...
    py -3 -m venv ".venv"
    if errorlevel 1 goto :error
)

echo Checking/installing app packages...
".venv\Scripts\python.exe" -m pip install -r "requirements.txt"
if errorlevel 1 goto :error

".venv\Scripts\python.exe" "hand_cursor.py"
if errorlevel 1 goto :error
exit /b 0

:error
echo.
echo Setup or startup failed. Check the message above and try again.
pause
exit /b 1
