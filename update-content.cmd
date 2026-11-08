@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\update-cs15content.ps1" -ServerDirectory "%~dp0CS15Server"
if errorlevel 1 pause
