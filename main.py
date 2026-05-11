"""
Omni Core V2 - Inicializador Principal
Modo simplificado: sempre GUI, sempre admin check, sem argumentos complexos.
"""

import sys
import logging
from pathlib import Path

# Diretório base (simplificado)
BASE_PATH = Path(__file__).resolve().parent
if str(BASE_PATH) not in sys.path:
    sys.path.insert(0, str(BASE_PATH))

from core.launcher import run_app

# Setup de logging simples
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

if __name__ == "__main__":
    run_app()


