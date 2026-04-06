@echo off
title Trading Value V2 Auto-Train
cd /d "C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value"

echo Starting V2 Auto-Train...
set PYTHONPATH=src
start "V2-Dashboard" /min py -3.12 scripts\dashboard_v2.py
timeout /t 3 >nul
start "V2-Train" py -3.12 scripts\auto_train_v2.py --steps 500000 --cycles 10 --resume

echo.
echo Dashboard: http://localhost:8893
echo Training: http://localhost:8891
echo.
pause
