@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Update-CS15Content.ps1" -ServerDirectory "%~dp0CS15Server"
if errorlevel 1 pause
