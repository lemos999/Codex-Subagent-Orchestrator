@echo off
title Strategy Tournament (5,000 variants)
cd /d "C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value"
echo Strategy Tournament - 5,000 variants x 9 assets x 7 strategies x 6 timeframes
echo Dashboard: http://localhost:8895
echo.
py -3.12 -u scripts\tournament.py
pause
