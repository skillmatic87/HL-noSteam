@echo off
setlocal DisableDelayedExpansion
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Start-CS15Server.ps1" %*
set "CS15_START_RESULT=%ERRORLEVEL%"
if not "%CS15_START_RESULT%"=="0" (
  echo.
  echo Server startup failed. Read the message above.
  pause
)
exit /b %CS15_START_RESULT%
