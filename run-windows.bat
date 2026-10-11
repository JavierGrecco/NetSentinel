@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_CMD=py -3"
%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 set "PYTHON_CMD=python"

%PYTHON_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if errorlevel 1 goto python_error

if not exist ".venv\Scripts\python.exe" (
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 goto venv_error
)

".venv\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if errorlevel 1 goto old_venv_error

".venv\Scripts\python.exe" -m pip install -e .
if errorlevel 1 goto install_error

echo.
echo NetSentinel se abrira en http://127.0.0.1:8765
".venv\Scripts\python.exe" -m netsentinel
echo.
echo NetSentinel se detuvo.
pause
endlocal
exit /b 0

:python_error
echo NetSentinel requiere Python 3.10 o posterior.
echo Instala Python desde https://www.python.org/downloads/ y volve a intentar.
pause
exit /b 1

:venv_error
echo No se pudo crear el entorno virtual .venv.
pause
exit /b 1

:old_venv_error
echo El entorno .venv existente usa una version vieja de Python.
echo Renombra o elimina la carpeta .venv y volve a ejecutar este archivo.
pause
exit /b 1

:install_error
echo No se pudieron instalar las dependencias. Revisa la conexion a Internet.
pause
exit /b 1
