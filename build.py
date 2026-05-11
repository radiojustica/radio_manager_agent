import os
import subprocess
import sys
import logging
from pathlib import Path

# Configuração de Log para o Build
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("build_process.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("OmniCore.Build")

def build():
    """
    Constrói o executável do Omni Core V2 usando PyInstaller.
    Inclui tratamento de erros detalhado e logs de saída.
    """
    logger.info("Iniciando processo de build do Omni Core V2...")
    
    # Caminho do ponto de entrada
    entry_point = "main.py"
    if not os.path.exists(entry_point):
        logger.error(f"Ponto de entrada '{entry_point}' não encontrado!")
        return False

    # Comando do PyInstaller
    # --onefile: gera um único executável
    # --noconsole: não abre janela de console (útil para GUI/Tray)
    # --hidden-import: garante que dependências dinâmicas sejam incluídas
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--console", # Mantemos console para debug por enquanto
        "--name", "omni_core",
        "--clean",
        "--add-data", "config;config",
        "--add-data", "core;core",
        "--add-data", "frontend/dist;frontend/dist",
        entry_point
    ]

    try:
        logger.info(f"Executando comando: {' '.join(cmd)}")
        
        # Executa o subprocesso capturando stdout e stderr
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        # Loga a saída em tempo real
        if process.stdout:
            for line in process.stdout:
                line = line.strip()
                if line:
                    logger.info(f"[PyInstaller] {line}")

        process.wait()

        if process.returncode == 0:
            logger.info("✅ Build concluído com sucesso!")
            return True
        else:
            logger.error(f"❌ PyInstaller encerrou com código de erro: {process.returncode}")
            return False

    except subprocess.SubprocessError as se:
        logger.critical(f"💥 Erro de Subprocesso durante o build: {se}")
        return False
    except Exception as e:
        logger.critical(f"🚨 Erro inesperado durante o build: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = build()
    sys.exit(0 if success else 1)
