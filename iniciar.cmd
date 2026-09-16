@echo off
setlocal
cd /d "%~dp0"
if not exist "Backend\.env" (
  echo Configure Backend\.env antes de iniciar. Consulte guia.md.
  pause
  exit /b 1
)
if not exist ".runtime\Scripts\python.exe" (
  echo Execute preparar.cmd primeiro.
  pause
  exit /b 1
)
".runtime\Scripts\python.exe" Backend\launch.py
if errorlevel 1 pause
endlocal
