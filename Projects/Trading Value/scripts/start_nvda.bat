@echo off
title NVDA Paper Trading
cd /d "C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value"
echo Starting NVDA Regime Paper Trading...
echo Dashboard: http://localhost:8897
py -3.12 -u scripts\paper_nvda.py
pause
