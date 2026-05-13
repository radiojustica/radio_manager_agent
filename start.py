"""
Omni Core V2 - Inicializador Simplificado
Modo operacional: API + Workers + Frontend auto-open
"""

import sys
import os
import logging
import threading
import time
import webbrowser
from pathlib import Path

# Diretório base
BASE_PATH = Path(__file__).resolve().parent
if str(BASE_PATH) not in sys.path:
    sys.path.insert(0, str(BASE_PATH))

# Setup de logging antecipado
log_dir = Path(r"D:\RADIO\LOG ZARARADIO")
log_dir.mkdir(exist_ok=True, parents=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_dir / "omni_core.log", encoding='utf-8')
    ],
    force=True
)

logger = logging.getLogger("OmniCore.Startup")

def open_browser_when_ready():
    """Aguarda a API estar pronta e abre o navegador automaticamente."""
    from api.manager import wait_for_server
    
    logger.info("⏳ Aguardando que a API esteja pronta...")
    if wait_for_server(timeout=30):
        time.sleep(1)  # Aguarda 1 segundo extra para garantir que a API está totalmente operacional
        try:
            logger.info("🌐 Abrindo dashboard no navegador...")
            webbrowser.open("http://localhost:8001")
            logger.info("✓ Dashboard aberto em http://localhost:8001")
        except Exception as e:
            logger.warning(f"Não foi possível abrir o navegador automaticamente: {e}")
    else:
        logger.warning("⚠️ Timeout ao aguardar API. Dashboard disponível em http://localhost:8001")

try:
    logger.info("=" * 70)
    logger.info("OMNI CORE V2 - INICIALIZANDO")
    logger.info("=" * 70)
    
    # Imports principais
    from api.manager import run_api_server
    
    if __name__ == "__main__":
        logger.info("🚀 Iniciando API...")
        
        # Inicia thread para abrir o navegador quando a API estiver pronta
        browser_thread = threading.Thread(target=open_browser_when_ready, daemon=True)
        browser_thread.start()
        
        # Inicia a API (bloqueia aqui)
        run_api_server()

except KeyboardInterrupt:
    logger.info("⏹️  Interrupção do usuário detectada.")
    sys.exit(0)

except Exception as e:
    import traceback
    logger.error("\n" + "=" * 70)
    logger.error("ERRO CRÍTICO NA INICIALIZAÇÃO:")
    logger.error("=" * 70)
    logger.error(traceback.format_exc())
    logger.error("=" * 70)
    sys.exit(1)
