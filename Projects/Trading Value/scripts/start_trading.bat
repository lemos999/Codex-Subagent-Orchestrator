@echo off
title Trading Value - Paper Trading
cd /d "C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value"
set PYTHONPATH=src

echo Starting dashboard...
start "Dashboard" /min py -3.12 scripts\dashboard_all.py

echo Starting paper trading bot...
ping -n 4 127.0.0.1 >nul

echo Opening browser...
start http://localhost:8889/

echo.
echo Dashboard: http://localhost:8889/
echo Bot: running in foreground
echo Press Ctrl+C to stop.
echo.

:loop
py -3.12 scripts\run_paper_all.py
if %errorlevel%==0 (
    echo Bot stopped normally.
    goto end
)
echo.
echo [%date% %time%] Bot crashed (exit code %errorlevel%), restarting in 30s...
ping -n 31 127.0.0.1 >nul
goto loop

:end
echo Done.
pause
