@echo off
title Multi-Asset Paper Trading
cd /d "C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value"
echo Starting Multi-Asset Paper Trading (BTC, NVDA, AMZN)...
echo Dashboard: http://localhost:8896
echo.
py -3.12 -u scripts\paper_multi.py
pause
