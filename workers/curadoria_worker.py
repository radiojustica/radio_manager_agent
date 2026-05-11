import os
import shutil
import logging
import asyncio
from datetime import datetime
from typing import Any

from core.worker_base import WorkerBase, WorkerResult
from core.reward import RewardStore
from services.curadoria_worker import processar_arquivo
from services.gemini_service import gemini_service

logger = logging.getLogger("OmniCore.Workers.Curadoria")

class CuradoriaWorker(WorkerBase):
    """
    Worker responsável pela auditoria acústica e curadoria de arquivos (Quarentena).
    Consome a lógica de services/curadoria_worker.py de forma estruturada e 
    enriquece metadados (Mood) via Gemini AI.
    """
    def __init__(self, reward_store: RewardStore | None = None, config: dict[str, Any] | None = None):
        super().__init__(name="CuradoriaWorker", reward_store=reward_store, config=config)
        self.batch_size = self.config.get("batch_size", 10)

    def run_cycle(self, **kwargs) -> WorkerResult:
        from core.database import SessionLocal, init_db
        from core.models import Musica
        
        # Garante que a coluna 'mood' exista (migração automática simples)
        init_db()
        
        db = SessionLocal()
        violations = []
        metadata = {"processed_count": 0, "quarantined_count": 0, "moods_classified": 0, "errors": 0}
        score = 0

        try:
            # 1. Auditoria Acústica (Padrão)
            pendentes_auditoria = db.query(Musica).filter(Musica.auditado_acustica == False).order_by(Musica.id.asc()).limit(self.batch_size).all()
            
            for musica in pendentes_auditoria:
                try:
                    resultado = processar_arquivo(musica.id, musica.caminho)
                    metadata["processed_count"] += 1
                    
                    musica.auditado_acustica = True
                    musica.duracao = resultado.get("duracao", 0)
                    
                    if resultado["status"] == "QUARANTINED":
                        musica.redflag = True
                        metadata["quarantined_count"] += 1
                        violations.append(f"Música {musica.id} enviada para quarentena: {resultado.get('motivo')}")
                        score += 5
                    else:
                        musica.energia = resultado.get("energia", 3)
                        score += 2
                    
                    db.commit()
                except Exception as e:
                    logger.error(f"Erro ao processar acústica da música {musica.id}: {e}")
                    metadata["errors"] += 1
                    db.rollback()

            # 2. Classificação de Mood via Gemini AI
            # Músicas que já passaram pela auditoria mas não têm mood definido
            pendentes_mood = db.query(Musica).filter(Musica.auditado_acustica == True, Musica.redflag == False, Musica.mood == None).limit(5).all()
            
            for musica in pendentes_mood:
                try:
                    # Roda a tarefa assíncrona de forma síncrona dentro da thread do worker
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    mood = loop.run_until_complete(gemini_service.classify_mood(musica.artista, musica.titulo))
                    loop.close()
                    
                    if mood:
                        musica.mood = mood
                        metadata["moods_classified"] += 1
                        score += 3
                        logger.info(f"Gemini: Música {musica.id} classificada como {mood}")
                        db.commit()
                except Exception as e:
                    logger.error(f"Erro ao classificar mood da música {musica.id}: {e}")
                    db.rollback()

            if metadata["processed_count"] == 0 and metadata["moods_classified"] == 0:
                return WorkerResult(status="idle", score=1, metadata={"message": "Nenhuma música pendente."})

            status = "success" if metadata["errors"] == 0 else "partial_success"
            return WorkerResult(status=status, score=score, violations=violations, metadata=metadata)

        except Exception as e:
            logger.error(f"Falha crítica no ciclo de curadoria: {e}")
            return WorkerResult(status="error", score=-10, violations=[str(e)], metadata=metadata)
        finally:
            db.close()
