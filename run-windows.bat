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

".venv\Scripts\python.exe" -c "import hashlib,pathlib,sys; marker=pathlib.Path('.venv/.netsentinel-install-hash'); expected=hashlib.sha256(pathlib.Path('pyproject.toml').read_bytes()).hexdigest(); raise SystemExit(0 if marker.is_file() and marker.read_text(encoding='ascii').strip()==expected else 1)" >nul 2>&1
if errorlevel 1 goto install_deps

".venv\Scripts\python.exe" -c "import fastapi,psutil,uvicorn,netsentinel,pathlib; raise SystemExit(0 if pathlib.Path(netsentinel.__file__).resolve()==pathlib.Path('src/netsentinel/__init__.py').resolve() else 1)" >nul 2>&1
if errorlevel 1 goto install_deps
goto run_app

:install_deps
".venv\Scripts\python.exe" -m pip install -e .
if errorlevel 1 goto install_error
".venv\Scripts\python.exe" -c "import hashlib,pathlib; pathlib.Path('.venv/.netsentinel-install-hash').write_text(hashlib.sha256(pathlib.Path('pyproject.toml').read_bytes()).hexdigest(), encoding='ascii')"
if errorlevel 1 goto install_error

:run_app
echo.
echo NetSentinel se abrira en http://127.0.0.1:8765
".venv\Scripts\python.exe" -m netsentinel
set "NETSENTINEL_EXIT_CODE=%ERRORLEVEL%"
echo.
if "%NETSENTINEL_EXIT_CODE%"=="0" (
    echo NetSentinel se detuvo correctamente.
) else (
    echo NetSentinel finalizo con error (codigo %NETSENTINEL_EXIT_CODE%).
)
pause
endlocal & exit /b %NETSENTINEL_EXIT_CODE%

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
