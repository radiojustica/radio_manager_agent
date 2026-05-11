import logging
from pathlib import Path

def setup_global_logging():
    log_dir = Path(r"D:\RADIO\LOG ZARARADIO")
    log_dir.mkdir(exist_ok=True, parents=True)
    log_file = log_dir / "omni_system.log"

    # Limpa handlers anteriores
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | [%(name)s] %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, encoding='utf-8')
        ],
        force=True
    )
    return logging.getLogger("OmniCore")


