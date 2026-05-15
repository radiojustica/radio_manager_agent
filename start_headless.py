"""
OMNI CORE V2 - Headless Starter
Starts API and Worker Manager without GUI or Admin elevation.
"""
import sys
import logging
import threading
import time
from pathlib import Path

# Base directory
BASE_PATH = Path(__file__).resolve().parent
if str(BASE_PATH) not in sys.path:
    sys.path.insert(0, str(BASE_PATH))

# Setup logging
log_dir = Path(r"D:\RADIO\LOG ZARARADIO")
log_dir.mkdir(exist_ok=True, parents=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_dir / "omni_headless.log", encoding='utf-8')
    ],
    force=True
)

logger = logging.getLogger("OmniCore.Headless")

def main():
    logger.info("Iniciando OMNI CORE V2 em modo Headless...")
    
    try:
        from api.manager import run_api_server
        from worker_manager import worker_manager_instance
        
        logger.info("Iniciando API em background...")
        api_thread = threading.Thread(target=run_api_server, daemon=True)
        api_thread.start()
        
        logger.info("Sistema operacional em modo headless. Dashboard em http://localhost:8001")
        
        # Keep alive
        while True:
            time.sleep(60)
            
    except Exception as e:
        logger.error(f"Erro fatal: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
