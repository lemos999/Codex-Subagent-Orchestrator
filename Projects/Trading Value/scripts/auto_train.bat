@echo off
title Auto-Train v2 - C Castle
cd /d "C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value"
set PYTHONPATH=src
set OMP_NUM_THREADS=1
set MKL_NUM_THREADS=1
set TORCH_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1

echo ============================================
echo   Auto-Train v2
echo   Dashboard: http://localhost:8891
echo   Press Ctrl+C to stop.
echo ============================================
echo.

start http://localhost:8891/
py -3.12 scripts\auto_train.py --model C

echo.
echo Done.
pause
