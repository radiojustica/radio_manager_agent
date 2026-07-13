# iniciar_streaming.py
import os
import subprocess
import time
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger("OmniCore.StreamingStart")

PASTA_CONF = Path(r"D:\butt_configs")
# Caminho detectado no ambiente do usuário
CAMINHO_BUTT_EXE = Path(r"D:\butt\butt.exe")

def iniciar_instancias():
    if not CAMINHO_BUTT_EXE.exists():
        logger.error(f"❌ butt.exe não encontrado em: {CAMINHO_BUTT_EXE}")
        # Tenta fallback para caminhos comuns
        fallbacks = [
            r"C:\Program Files (x86)\butt\butt.exe",
            r"C:\Program Files\butt\butt.exe"
        ]
        found = False
        for fb in fallbacks:
            if Path(fb).exists():
                globals()['CAMINHO_BUTT_EXE'] = Path(fb)
                found = True
                break
        if not found:
            logger.info("Por favor, verifique a instalação do BUTT.")
            return

    logger.info(f"🔍 Buscando configurações em: {PASTA_CONF}")
    
    if not PASTA_CONF.exists():
        logger.error(f"Pasta de configurações não encontrada: {PASTA_CONF}")
        return

    arquivos_butt = list(PASTA_CONF.glob("*.butt"))

    if not arquivos_butt:
        logger.warning("Nenhum arquivo de configuração .butt encontrado.")
        return

    logger.info(f"🚀 Iniciando {len(arquivos_butt)} instâncias do BUTT...")

    for config_path in arquivos_butt:
        try:
            # O parâmetro -c força o BUTT a usar um arquivo de configuração específico
            comando = [str(CAMINHO_BUTT_EXE), '-c', str(config_path)]
            
            # Abre o processo em segundo plano
            subprocess.Popen(comando, creationflags=subprocess.DETACHED_PROCESS)
            logger.info(f"✅ Iniciado: {config_path.name}")
            
            # Pausa de 5 segundos para não sobrecarregar o driver de áudio
            time.sleep(5) 
            
        except Exception as e:
            logger.error(f"❌ Falha ao iniciar {config_path}: {e}")

    logger.info("🎉 Todas as instâncias do BUTT foram lançadas!")
    logger.info("O Omni Daemon assumirá o controle e conectará ao Icecast automaticamente.")

if __name__ == "__main__":
    iniciar_instancias()
