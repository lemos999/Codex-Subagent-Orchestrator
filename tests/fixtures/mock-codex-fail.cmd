@echo off
set MOCK_CODEX_MODE=fail
node "%~dp0mock-codex.js" %*
