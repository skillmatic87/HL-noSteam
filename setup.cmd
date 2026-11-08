@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install-cs15server.ps1"
if errorlevel 1 (
  echo.
  echo Setup did not complete. Read the error above before trying again.
)
pause
