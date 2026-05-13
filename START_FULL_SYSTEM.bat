@echo off
title Omni Core V2 - Full System Launcher
echo ====================================================
echo   OMNI CORE V2 - INICIALIZADOR COMPLETO
echo ====================================================
echo.

:: Verifica se o Python está no PATH
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado no PATH.
    pause
    exit /b
)

:: Verifica se o Node.js está no PATH
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Node.js nao encontrado no PATH.
    pause
    exit /b
)

echo [1/3] Iniciando Backend (Omni Core)...
start "Omni Backend" /min python main.py

echo [2/3] Iniciando Frontend (Vite)...
cd frontend
start "Omni Frontend" /min npm run dev
cd ..

echo [3/3] Aguardando inicializacao...
timeout /t 5 /nobreak >nul

echo.
echo ====================================================
echo   SISTEMA ONLINE!
echo.
echo   - DASHBOARD: http://localhost:5173
echo   - API DOCS: http://localhost:8001/docs
echo ====================================================
echo.
echo Pressione qualquer tecla para abrir o Dashboard no navegador...
pause >nul

start http://localhost:5173

echo.
echo O sistema continuara rodando em segundo plano.
echo Para fechar tudo, feche as janelas minimizadas do CMD.
pause
