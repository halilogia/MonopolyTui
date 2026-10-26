@echo off
setlocal
cd /d "%~dp0"
where wt >nul 2>nul
if %errorlevel%==0 (
    start "" wt -w new --size 125,38 -d "%CD%." python main.py
) else (
    python main.py
)
endlocal
