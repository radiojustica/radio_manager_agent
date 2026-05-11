import os
import logging
from datetime import datetime, UTC
from typing import Any

from core.worker_base import WorkerBase, WorkerResult
from core.reward import RewardStore
from core.database import SessionLocal
from core.models import Musica

logger = logging.getLogger("OmniCore.Workers.Sync")

class SyncWorker(WorkerBase):
    """
    Worker responsável pela sincronização entre o banco de dados e os arquivos físicos em disco.
    Adiciona novos arquivos e remove referências a arquivos inexistentes.
    """
    def __init__(self, reward_store: RewardStore | None = None, config: dict[str, Any] | None = None):
        super().__init__(name="SyncWorker", reward_store=reward_store, config=config)
        self.music_path = self.config.get("music_path", r"D:\RADIO\MUSICAS")

    def run_cycle(self, **kwargs) -> WorkerResult:
        if not os.path.exists(self.music_path):
            return WorkerResult(status="error", score=-5, violations=[f"Pasta de músicas não encontrada: {self.music_path}"])

        db = SessionLocal()
        novos = 0
        removidos = 0
        mantidos = 0
        violations = []

        try:
            # Mapeia caminhos no banco
            caminhos_db = {m.caminho for m in db.query(Musica.caminho).all()}
            caminhos_fisicos = set()

            # Varredura no disco
            for root, _, files in os.walk(self.music_path):
                for file in files:
                    if file.lower().endswith('.mp3'):
                        caminho = os.path.join(root, file)
                        caminhos_fisicos.add(caminho)
                        
                        if caminho not in caminhos_db:
                            try:
                                artista = file.split(" - ")[0] if " - " in file else "VARIOUS"
                                titulo = file.split(" - ")[1].replace(".mp3", "") if " - " in file else file.replace(".mp3", "")
                                
                                nova_musica = Musica(
                                    caminho=caminho,
                                    titulo=titulo,
                                    artista=artista.upper(),
                                    estilo="outros",
                                    energia=3,
                                    auditado_acustica=False,
                                    redflag=False,
                                    ultima_reproducao=datetime.now(UTC)
                                )
                                db.add(nova_musica)
                                novos += 1
                            except Exception as e:
                                logger.error(f"Erro ao adicionar arquivo {file}: {e}")
                                violations.append(f"Erro ao adicionar {file}: {e}")
                        else:
                            mantidos += 1
                
                # Commit parcial a cada 100 arquivos para não estourar memória
                if (novos + mantidos) % 100 == 0:
                    db.commit()

            # Limpeza de registros sem arquivo físico
            zumbis = caminhos_db - caminhos_fisicos
            for caminho_zumbi in zumbis:
                db.query(Musica).filter(Musica.caminho == caminho_zumbi).delete()
                removidos += 1
                
            db.commit()

            score = 1
            if novos > 0: score += 2 # Bônus por novos arquivos encontrados
            if removidos > 0: score += 1 # Bônus por manter o banco limpo

            metadata = {
                "novos": novos,
                "removidos": removidos,
                "mantidos": mantidos,
                "total_banco": len(caminhos_fisicos)
            }

            return WorkerResult(status="success", score=score, violations=violations, metadata=metadata)

        except Exception as e:
            db.rollback()
            logger.error(f"Erro crítico no SyncWorker: {e}")
            return WorkerResult(status="error", score=-10, violations=[str(e)], metadata={"error": str(e)})
        finally:
            db.close()
