@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Preparando el entorno de NOCTURNE...
    python -m venv .venv
    if errorlevel 1 goto python_error
)
".venv\Scripts\python.exe" -c "import panda3d" >nul 2>&1
if errorlevel 1 (
    echo Instalando Panda3D...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto install_error
)
".venv\Scripts\python.exe" main.py %*
if errorlevel 1 (
    echo.
    echo No se pudo iniciar el juego. Consulta README.md o prueba Jugar.cmd --quality low.
    pause
)
exit /b
:python_error
echo Instala Python 3.10 o superior y activa "Add Python to PATH".
pause
exit /b 1
:install_error
echo No se pudo instalar Panda3D. Comprueba tu conexion y ejecuta de nuevo.
pause
exit /b 1
