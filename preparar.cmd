@echo off
setlocal
cd /d "%~dp0"
if not exist ".runtime\Scripts\python.exe" (
  py -3 -m venv .runtime
  if errorlevel 1 (
    echo Instale Python 3.12 ou superior e tente novamente.
    pause
    exit /b 1
  )
)
".runtime\Scripts\python.exe" -m pip install -r Backend\requirements.txt
if errorlevel 1 goto :failed
call npm.cmd ci --prefix Frontend
if errorlevel 1 goto :failed
call npm.cmd run build --prefix Frontend
if errorlevel 1 goto :failed
".runtime\Scripts\python.exe" Backend\manage.py migrate
if errorlevel 1 goto :failed
echo NexusGest preparado. Abra iniciar.cmd para acessar.
pause
exit /b 0
:failed
echo Nao foi possivel preparar o projeto. Confira o erro acima e o guia.md.
pause
exit /b 1
