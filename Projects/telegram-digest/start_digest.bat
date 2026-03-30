@echo off
title Telegram Digest
cd /d "%~dp0"
set retries=0
set max_retries=3

:loop
set /a retries+=1
echo [%date% %time%] Starting Telegram Digest (attempt %retries%/%max_retries%)...
py -3.12 main.py
set exitcode=%errorlevel%

if %exitcode%==0 (
    echo [%date% %time%] Normal exit.
    goto end
)

if %retries% geq %max_retries% (
    echo [%date% %time%] %max_retries% attempts failed. Running diagnostics...
    py -3.12 diagnose.py
    goto end
)

echo [%date% %time%] Exited with code %exitcode%. Restarting in 30 seconds...
timeout /t 30 /nobreak >nul
goto loop

:end
echo [%date% %time%] Telegram Digest stopped.
pause
