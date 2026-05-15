@echo off
title Omni Core V2 Launcher
echo ====================================================
echo   OMNI CORE V2 - INICIALIZADOR MESTRE
echo ====================================================
cd /d "%~dp0"

:: Garante que o diretório atual está no PYTHONPATH para evitar erros de import
set PYTHONPATH=%cd%;%PYTHONPATH%

echo [1/1] Verificando dependencias e iniciando sistema...
echo.

:: Tenta rodar o main.py que gerencia a GUI e Elevacao Admin
python main.py

if %errorlevel% neq 0 (
    echo.
    echo [ERRO] O sistema fechou com erro (codigo %errorlevel%^).
    echo Verifique se o Python esta instalado e se as dependencias estao no PATH.
    echo.
    pause
)
