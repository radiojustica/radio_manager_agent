@echo off
title Omni Core V2 Launcher
echo ====================================================
echo   OMNI CORE V2 - INICIALIZADOR
echo ====================================================
cd /d "%~dp0"
set PYTHONPATH=%PYTHONPATH%;%cd%
python start.py
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao iniciar o sistema.
    pause
)
