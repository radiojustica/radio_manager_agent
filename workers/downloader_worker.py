import os
import logging
from typing import Any

from core.worker_base import WorkerBase, WorkerResult
from core.reward import RewardStore
from services.downloader_service import downloader_instance
from core.database import SessionLocal
from core.models import Musica
from sqlalchemy import or_, and_

logger = logging.getLogger("OmniCore.Workers.Downloader")

class DownloaderWorker(WorkerBase):
    """
    Worker responsável pelo processamento de downloads de músicas.
    Atua sob demanda (via UI) ou de forma proativa (automática).
    """
    def __init__(self, reward_store: RewardStore | None = None, config: dict[str, Any] | None = None):
        super().__init__(name="DownloaderWorker", reward_store=reward_store, config=config)
        self.proactive_limit = self.config.get("proactive_limit", 3)

    def run_cycle(self, queries: list[str] | None = None, estilo: str = "outros", **kwargs) -> WorkerResult:
        is_proactive = queries is None
        
        if is_proactive:
            from director.recommender import recommender_instance
            logger.info("[DownloaderWorker] Iniciando ciclo proativo de aquisição.")
            try:
                analysis = recommender_instance.analyze_last_days(5)
                recs = recommender_instance.generate_recommendations(analysis)
                if not recs:
                    return WorkerResult(status="idle", score=0, metadata={"message": "Nenhuma recomendação proativa encontrada."})
                
                queries = [r["sugestao"] for r in recs[:self.proactive_limit]]
                logger.info(f"[DownloaderWorker] {len(queries)} sugestões selecionadas para download automático.")
            except Exception as e:
                logger.error(f"[DownloaderWorker] Erro ao gerar recomendações: {e}", exc_info=True)
                return WorkerResult(
                    status="failed",
                    score=-10,
                    violations=[f"Erro ao gerar recomendações: {str(e)}"],
                    metadata={"message": str(e)}
                )

        if not queries:
            return WorkerResult(status="idle", score=0, metadata={"message": "Nenhuma query de download fornecida."})

        results = []
        violations = []
        score = 0
        metadata = {"processed": 0, "success": 0, "failed": 0, "skipped": 0, "proactive": is_proactive}

        db = SessionLocal()
        try:
            for query in queries:
                metadata["processed"] += 1
                try:
                    # Verifica se já temos algo similar no banco para evitar duplicidade
                    clean_query = query.replace(" - Greatest Hits", "").strip()
                    existing = db.query(Musica).filter(
                        or_(
                            Musica.caminho.like(f"%{clean_query}%"),
                            and_(
                                Musica.artista.ilike(f"%{clean_query.split(' - ')[0]}%"),
                                Musica.titulo.ilike(f"%{clean_query.split(' - ')[-1]}%")
                            ) if " - " in clean_query else False
                        )
                    ).first()
                    
                    if existing:
                        logger.info(f"[DownloaderWorker] Query '{query}' já existe no acervo (ID: {existing.id}). Pulando.")
                        metadata["skipped"] += 1
                        results.append({"query": query, "status": "skipped", "reason": "already_exists"})
                        continue

                    # Tenta download com tratamento específico de timeout
                    res = downloader_instance.search_and_download(query)
                    
                    if res["success"]:
                        file_path = res["path"]
                        metadata["success"] += 1
                        score += 10 if is_proactive else 5

                        filename = os.path.basename(file_path).replace(".mp3", "")
                        
                        yt_title = res.get("title", "")
                        if " - " in yt_title:
                            art, tit = yt_title.split(" - ", 1)
                        elif " - " in filename:
                            art, tit = filename.split(" - ", 1)
                        else:
                            art, tit = "VÁRIOS", filename
                        
                        art = art.strip().upper()
                        tit = tit.strip()

                        # Verifica duplicidade antes de inserir
                        musica_existente = db.query(Musica).filter(Musica.caminho == file_path).first()
                        if not musica_existente:
                            nova_musica = Musica(
                                caminho=file_path,
                                artista=art,
                                titulo=tit,
                                estilo=estilo.lower(),
                                auditado_acustica=False
                            )
                            db.add(nova_musica)
                            db.commit()
                            results.append({"query": query, "status": "success", "file": filename, "id": nova_musica.id})
                            logger.info(f"[DownloaderWorker] Música catalogada: {art} - {tit}")
                        else:
                            metadata["skipped"] += 1
                            metadata["success"] -= 1
                            results.append({"query": query, "status": "skipped", "reason": "already_in_db"})
                            logger.info(f"[DownloaderWorker] Arquivo já no banco: {file_path}")
                    else:
                        metadata["failed"] += 1
                        score -= 2
                        error_msg = res.get("error", "Erro desconhecido")
                        violations.append(f"Download falhou para '{query}': {error_msg}")
                        results.append({"query": query, "status": "failed", "error": error_msg})
                        logger.error(f"[DownloaderWorker] Download falhou: {query} - {error_msg}")
                        
                except TimeoutError as e:
                    metadata["failed"] += 1
                    score -= 3
                    error_msg = f"Timeout ao processar: {str(e)}"
                    violations.append(error_msg)
                    results.append({"query": query, "status": "failed", "error": "timeout"})
                    logger.error(f"[DownloaderWorker] Timeout: {query}")
                except Exception as e:
                    metadata["failed"] += 1
                    score -= 5
                    error_msg = f"Erro inesperado: {str(e)}"
                    logger.error(f"[DownloaderWorker] Erro ao processar '{query}': {e}", exc_info=True)
                    violations.append(error_msg)
                    results.append({"query": query, "status": "failed", "error": str(e)})
        finally:
            db.close()

        status = "success" if metadata["failed"] == 0 else "partial_success"
        if metadata["success"] == 0 and metadata["processed"] > 0:
            status = "failed"

        metadata["results"] = results
        return WorkerResult(status=status, score=score, violations=violations, metadata=metadata)
