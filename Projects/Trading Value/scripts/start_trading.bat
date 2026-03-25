@echo off
title Trading Value - Paper Trading
cd /d "C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value"
set PYTHONPATH=src

echo Starting dashboard...
start /b py -3 scripts\dashboard_all.py

echo Starting paper trading bot...
timeout /t 3 /nobreak >nul

echo Opening browser...
start http://localhost:8889/

echo.
echo Dashboard: http://localhost:8889/
echo Bot: running in background
echo Press Ctrl+C to stop all.
echo.

:loop
py -3 scripts\run_paper_all.py
echo Bot crashed, restarting in 30s...
timeout /t 30
goto loop
