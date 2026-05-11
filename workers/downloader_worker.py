import os
import logging
from typing import Any

from core.worker_base import WorkerBase, WorkerResult
from core.reward import RewardStore
from services.downloader_service import downloader_instance
from core.database import SessionLocal
from core.models import Musica

logger = logging.getLogger("OmniCore.Workers.Downloader")

class DownloaderWorker(WorkerBase):
    """
    Worker responsável pelo processamento de downloads de músicas.
    Atua principalmente sob demanda, mas pode ser expandido para auto-download.
    """
    def __init__(self, reward_store: RewardStore | None = None, config: dict[str, Any] | None = None):
        super().__init__(name="DownloaderWorker", reward_store=reward_store, config=config)

    def run_cycle(self, queries: list[str] | None = None, estilo: str = "outros", **kwargs) -> WorkerResult:
        if not queries:
            return WorkerResult(status="idle", score=0, metadata={"message": "Nenhuma query de download fornecida."})

        results = []
        violations = []
        score = 0
        metadata = {"processed": 0, "success": 0, "failed": 0}

        for query in queries:
            metadata["processed"] += 1
            try:
                res = downloader_instance.search_and_download(query)
                if res["success"]:
                    file_path = res["path"]
                    metadata["success"] += 1
                    score += 5 # Recompensa por download bem sucedido

                    # Cadastro no Banco
                    db = SessionLocal()
                    try:
                        filename = os.path.basename(file_path).replace(".mp3", "")
                        art, tit = "VARIOUS", filename
                        if " - " in filename:
                            art, tit = filename.split(" - ", 1)
                        
                        nova_musica = Musica(
                            caminho=file_path,
                            artista=art.strip().upper(),
                            titulo=tit.strip(),
                            estilo=estilo.lower(),
                            auditado_acustica=False
                        )
                        db.add(nova_musica)
                        db.commit()
                        results.append({"query": query, "status": "success", "file": filename})
                    except Exception as db_err:
                        logger.error(f"Erro ao cadastrar {filename}: {db_err}")
                        violations.append(f"Erro DB em {query}: {db_err}")
                    finally:
                        db.close()
                else:
                    metadata["failed"] += 1
                    score -= 2
                    violations.append(f"Falha no download de {query}: {res.get('error')}")
                    results.append({"query": query, "status": "failed", "error": res.get("error")})
            except Exception as e:
                metadata["failed"] += 1
                score -= 5
                logger.error(f"Erro crítico ao processar {query}: {e}")
                violations.append(f"Erro crítico em {query}: {e}")

        status = "success" if metadata["failed"] == 0 else "partial_success"
        if metadata["success"] == 0 and metadata["processed"] > 0:
            status = "failed"

        metadata["results"] = results
        return WorkerResult(status=status, score=score, violations=violations, metadata=metadata)
