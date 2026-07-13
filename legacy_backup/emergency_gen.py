
import os
import random
import logging
from core.database import SessionLocal
from core.models import Musica
from workers.playlist_worker import PlaylistWorker
from director.auditor import ProgrammingAuditor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EmergencyGen")

def generate_emergency_playlist():
    worker = PlaylistWorker()
    auditor = ProgrammingAuditor()
    
    # 1. Obter candidatas
    candidates = worker.listar_musicas_candidatas(limit=300)
    if not candidates:
        logger.error("Nenhuma música candidata encontrada!")
        return

    # 2. Gerar blocos de 2h
    for hora in range(0, 24, 2):
        logger.info(f"Gerando bloco de {hora:02d}H...")
        
        # Seleção simplificada: embaralha e pega 22 músicas
        # (Idealmente seguiria regras de energia, mas aqui é emergência)
        random.shuffle(candidates)
        selection = candidates[:22]
        caminhos = [t['caminho'] for t in selection]
        
        # 3. Gravar
        res = worker.gravar_playlist(caminhos, hora)
        logger.info(f"Bloco {hora:02d}H: {res}")

if __name__ == "__main__":
    generate_emergency_playlist()
