"""
Omni Core V2 - Inicializador Principal
Modo simplificado: sempre GUI, sempre admin check, sem argumentos complexos.
"""

import sys
import logging
from pathlib import Path

try:
    # Diretório base (simplificado)
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
            logging.FileHandler(log_dir / "omni_system.log", encoding='utf-8')
        ],
        force=True
    )

    logger = logging.getLogger("OmniCore.Main")
    logger.info("Iniciando setup do sistema...")

    from core.launcher import run_app

    if __name__ == "__main__":
        logger.info("Chamando run_app()...")
        run_app()

except Exception as e:
    import traceback
    print("\n" + "="*50)
    print("ERRO CRÍTICO NA INICIALIZAÇÃO:")
    print("="*50)
    traceback.print_exc()
    print("="*50)
    input("\nPressione Enter para sair...")
    sys.exit(1)


