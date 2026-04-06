@echo off
title BTC+AMZN Paper Trading
cd /d "C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value"
echo Starting BTC + AMZN Paper Trading...
echo Dashboard: http://localhost:8898
py -3.12 -u scripts\paper_btc_amzn.py
pause
