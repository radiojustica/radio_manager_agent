import os
import shutil
import logging
from datetime import datetime
from typing import Any

from core.worker_base import WorkerBase, WorkerResult
from core.reward import RewardStore
from services.curadoria_worker import processar_arquivo

logger = logging.getLogger("OmniCore.Workers.Curadoria")

class CuradoriaWorker(WorkerBase):
    """
    Worker responsável pela auditoria acústica e curadoria de arquivos (Quarentena).
    Consome a lógica de services/curadoria_worker.py de forma estruturada.
    """
    def __init__(self, reward_store: RewardStore | None = None, config: dict[str, Any] | None = None):
        super().__init__(name="CuradoriaWorker", reward_store=reward_store, config=config)
        self.batch_size = self.config.get("batch_size", 10)

    def run_cycle(self, **kwargs) -> WorkerResult:
        from core.database import SessionLocal
        from core.models import Musica
        
        db = SessionLocal()
        violations = []
        metadata = {"processed_count": 0, "quarantined_count": 0, "errors": 0}
        score = 0

        try:
            # Busca músicas pendentes de auditoria
            pendentes = db.query(Musica).filter(Musica.auditado_acustica == False).order_by(Musica.id.asc()).limit(self.batch_size).all()
            
            if not pendentes:
                return WorkerResult(status="idle", score=1, metadata={"message": "Nenhuma música pendente."})

            for musica in pendentes:
                try:
                    resultado = processar_arquivo(musica.id, musica.caminho)
                    metadata["processed_count"] += 1
                    
                    musica.auditado_acustica = True
                    musica.duracao = resultado.get("duracao", 0)
                    
                    if resultado["status"] == "QUARANTINED":
                        musica.redflag = True
                        metadata["quarantined_count"] += 1
                        violations.append(f"Música {musica.id} enviada para quarentena: {resultado.get('motivo')}")
                        score += 5 # Recompensa por identificar e isolar problema
                    else:
                        musica.energia = resultado.get("energia", 3)
                        score += 2 # Recompensa por auditoria bem sucedida
                    
                    db.commit()
                except Exception as e:
                    logger.error(f"Erro ao processar música {musica.id}: {e}")
                    metadata["errors"] += 1
                    db.rollback()

            status = "success" if metadata["errors"] == 0 else "partial_success"
            return WorkerResult(status=status, score=score, violations=violations, metadata=metadata)

        except Exception as e:
            logger.error(f"Falha crítica no ciclo de curadoria: {e}")
            return WorkerResult(status="error", score=-10, violations=[str(e)], metadata=metadata)
        finally:
            db.close()
