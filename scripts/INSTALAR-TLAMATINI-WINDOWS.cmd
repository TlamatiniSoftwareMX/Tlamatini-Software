@echo off
setlocal
title Instalador de TLAMATINI

rem Si este archivo viaja junto al instalador Full (por ejemplo, en una USB),
rem no se necesita Internet: se ejecuta directamente el instalador local.
set "OFFLINE_INSTALLER=%~dp0TLAMATINI-Windows-Instalador-Full.exe"
if exist "%OFFLINE_INSTALLER%" (
    echo.
    echo Iniciando el instalador local de TLAMATINI...
    start "" /wait "%OFFLINE_INSTALLER%"
    set "RESULT=%ERRORLEVEL%"
    if not "%RESULT%"=="0" pause
    exit /b %RESULT%
)

rem Este es el unico archivo que el usuario necesita descargar. El script de
rem PowerShell se obtiene desde la misma Release para poder actualizar el
rem proceso de instalacion sin pedir archivos adicionales al usuario.
set "REPOSITORY=TlamatiniSoftwareMX/Tlamatini-Software"
set "SCRIPT_URL=https://github.com/%REPOSITORY%/releases/latest/download/INSTALAR-TLAMATINI-WINDOWS.ps1"
set "BOOTSTRAP=%TEMP%\TLAMATINI-instalar-windows.ps1"

echo.
echo Preparando el instalador de TLAMATINI...
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -Uri '%SCRIPT_URL%' -OutFile '%BOOTSTRAP%'"
if errorlevel 1 (
    echo.
    echo No se pudo preparar el instalador. Comprueba tu conexion a Internet e intentalo de nuevo.
    pause
    exit /b 1
)

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%BOOTSTRAP%" -Repository "%REPOSITORY%"
set "RESULT=%ERRORLEVEL%"
del /q "%BOOTSTRAP%" >nul 2>&1
if not "%RESULT%"=="0" pause
exit /b %RESULT%
