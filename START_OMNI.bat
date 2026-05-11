@echo off
title Omni Core V2 Launcher
echo Iniciando Omni Core V2...
cd /d "%~dp0"
set PYTHONPATH=%PYTHONPATH%;%cd%
python core/launcher.py
pause
