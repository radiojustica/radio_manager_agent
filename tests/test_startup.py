"""
Script de teste para diagnosticar problemas de inicialização
Executa sem privilégios de admin e sem UI
"""

import sys
import logging
from pathlib import Path

# Diretório base
BASE_PATH = Path(__file__).resolve().parent
if str(BASE_PATH) not in sys.path:
    sys.path.insert(0, str(BASE_PATH))

# Setup de logging
log_dir = Path(r"D:\RADIO\LOG ZARARADIO")
log_dir.mkdir(exist_ok=True, parents=True)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_dir / "test_startup.log", encoding='utf-8')
    ],
    force=True
)

logger = logging.getLogger("OmniCore.TestStartup")

def test_imports():
    """Testa se todos os imports funcionam corretamente."""
    logger.info("=" * 60)
    logger.info("INICIANDO TESTES DE IMPORTAÇÃO")
    logger.info("=" * 60)
    
    try:
        logger.info("✓ Importando core.state...")
        from core import state
        logger.info("✓ core.state OK")
        
        logger.info("✓ Importando core.system...")
        from core.system import is_admin, verificar_instancia_unica, run_as_admin
        logger.info("✓ core.system OK")
        
        logger.info("✓ Importando core.database...")
        from core.database import engine, Base, SessionLocal
        logger.info("✓ core.database OK")
        
        logger.info("✓ Importando services.guardian_service...")
        from services.guardian_service import guardian_instance
        logger.info("✓ services.guardian_service OK")
        
        logger.info("✓ Importando worker_manager...")
        from worker_manager import worker_manager_instance
        logger.info("✓ worker_manager OK")
        
        logger.info("✓ Importando api.manager...")
        from api.manager import app
        logger.info("✓ api.manager OK")
        
        logger.info("=" * 60)
        logger.info("✓ TODOS OS IMPORTS ESTÃO OK")
        logger.info("=" * 60)
        return True
        
    except Exception as e:
        logger.error(f"✗ ERRO DURANTE IMPORTAÇÃO: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_api_startup():
    """Testa se a API pode ser iniciada em background."""
    try:
        logger.info("Testando inicialização da API...")
        from api.manager import app
        from api.manager import run_api_server
        import threading
        import time
        
        logger.info("Iniciando API em thread...")
        api_thread = threading.Thread(target=run_api_server, daemon=True)
        api_thread.start()
        
        logger.info("Aguardando inicialização da API (5 segundos)...")
        time.sleep(5)
        
        if api_thread.is_alive():
            logger.info("✓ API iniciou com sucesso")
            return True
        else:
            logger.error("✗ API foi interrompida")
            return False
            
    except Exception as e:
        logger.error(f"✗ ERRO ao testar API: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Executa todos os testes."""
    logger.info("\n")
    logger.info("*" * 60)
    logger.info("TESTE DE INICIALIZAÇÃO - OMNI CORE V2")
    logger.info(f"Data: {Path(__file__).resolve().parent.name}")
    logger.info("*" * 60)
    
    # Teste 1: Imports
    imports_ok = test_imports()
    
    # Teste 2: API
    if imports_ok:
        api_ok = test_api_startup()
    else:
        logger.error("Pulando teste de API due to import failures")
        api_ok = False
    
    # Relatório final
    logger.info("\n")
    logger.info("=" * 60)
    logger.info("RELATÓRIO FINAL")
    logger.info("=" * 60)
    logger.info(f"Imports: {'✓ OK' if imports_ok else '✗ FALHA'}")
    logger.info(f"API: {'✓ OK' if api_ok else '✗ FALHA'}")
    logger.info("=" * 60)
    
    return 0 if (imports_ok and api_ok) else 1

if __name__ == "__main__":
    sys.exit(main())
