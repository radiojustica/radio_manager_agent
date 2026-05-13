"""
Omni Core V2 - Inicializador Simplificado
Modo operacional: GUI + API + Workers, com fallback para modo sem admin
"""

import sys
import os
import logging
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

try:
    logger.info("=" * 70)
    logger.info("OMNI CORE V2 - INICIALIZANDO")
    logger.info("=" * 70)
    
    # Imports principais
    from core.launcher import run_app
    
    if __name__ == "__main__":
        logger.info("Iniciando aplicação...")
        run_app()

except KeyboardInterrupt:
    logger.info("Interrupção do usuário detectada.")
    sys.exit(0)

except Exception as e:
    import traceback
    logger.error("\n" + "=" * 70)
    logger.error("ERRO CRÍTICO NA INICIALIZAÇÃO:")
    logger.error("=" * 70)
    logger.error(traceback.format_exc())
    logger.error("=" * 70)
    
    # Fallback: tentar iniciar apenas a API sem UI
    try:
        logger.warning("Tentando iniciar em modo API-only (sem UI)...")
        from api.manager import run_api_server
        run_api_server()
    except Exception as e2:
        logger.error(f"Falha também no modo API-only: {e2}")
        sys.exit(1)
