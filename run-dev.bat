@echo off
REM Conductor ERP - double-click launcher. Runs run-dev.ps1 with no profile and
REM an execution-policy bypass so it works even on a locked-down machine.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run-dev.ps1"
echo.
echo Launcher finished. The API and frontend run in their own windows.
pause
