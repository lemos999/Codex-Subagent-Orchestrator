@echo off
title Trading Value - Unified Dashboard
cd /d "C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value"

echo === Trading Value - Unified Dashboard ===
echo.

echo [1/4] Starting Tournament (port 8895)...
start /min "" py -3.12 -u scripts\tournament.py

echo [2/4] Starting V2 Prediction Engine (port 8897)...
start /min "" py -3.12 -u scripts\v2.py

echo [3/4] Starting V3 Parker Brooks + Self-Learning (port 8898)...
start /min "" py -3.12 -u scripts\v3.py

echo [4/4] Starting Unified Dashboard (port 8900)...
timeout /t 5 /nobreak >nul
start "" http://localhost:8900
py -3.12 -u scripts\dashboard_unified.py

pause
