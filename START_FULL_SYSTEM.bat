@echo off
title Omni Core V2 - Full System Launcher
echo ====================================================
echo   OMNI CORE V2 - SISTEMA COMPLETO
echo ====================================================
cd /d "%~dp0"
set PYTHONPATH=%PYTHONPATH%;%cd%
echo [1/1] Iniciando Backend + Workers + UI...
python start.py
pause
