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
            analysis = recommender_instance.analyze_last_days(5)
            recs = recommender_instance.generate_recommendations(analysis)
            if not recs:
                return WorkerResult(status="idle", score=0, metadata={"message": "Nenhuma recomendação proativa encontrada."})
            
            # Pega apenas os top N para não sobrecarregar
            queries = [r["sugestao"] for r in recs[:self.proactive_limit]]
            logger.info(f"[DownloaderWorker] {len(queries)} sugestões selecionadas para download automático.")

        if not queries:
            return WorkerResult(status="idle", score=0, metadata={"message": "Nenhuma query de download fornecida."})

        results = []
        violations = []
        score = 0
        metadata = {"processed": 0, "success": 0, "failed": 0, "proactive": is_proactive}

        db = SessionLocal()
        try:
            for query in queries:
                metadata["processed"] += 1
                try:
                    # Verifica se já temos algo similar no banco para evitar duplicidade
                    # Normaliza a busca
                    clean_query = query.replace(" - Greatest Hits", "").strip()
                    existing = db.query(Musica).filter(
                        or_(
                            Musica.caminho.like(f"%{clean_query}%"),
                            and_(Musica.artista.ilike(f"%{clean_query.split(' - ')[0]}%"), Musica.titulo.ilike(f"%{clean_query.split(' - ')[-1]}%")) if " - " in clean_query else False
                        )
                    ).first()
                    
                    if existing:
                        logger.info(f"[DownloaderWorker] Query '{query}' já parece existir no acervo (ID: {existing.id}). Pulando.")
                        results.append({"query": query, "status": "skipped", "reason": "already_exists"})
                        continue

                    res = downloader_instance.search_and_download(query)
                    if res["success"]:
                        file_path = res["path"]
                        metadata["success"] += 1
                        score += 10 if is_proactive else 5 # Bônus por proatividade

                        filename = os.path.basename(file_path).replace(".mp3", "")
                        art, tit = "VARIOUS", filename
                        if " - " in filename:
                            art, tit = filename.split(" - ", 1)
                        
                        # Verifica se o caminho exato já existe (caso o like tenha falhado)
                        if not db.query(Musica).filter(Musica.caminho == file_path).first():
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
                        else:
                            results.append({"query": query, "status": "skipped", "reason": "path_exists"})
                    else:
                        metadata["failed"] += 1
                        score -= 2
                        violations.append(f"Falha no download de {query}: {res.get('error')}")
                        results.append({"query": query, "status": "failed", "error": res.get("error")})
                except Exception as e:
                    metadata["failed"] += 1
                    score -= 5
                    logger.error(f"Erro ao processar query '{query}': {e}")
                    violations.append(f"Erro em {query}: {str(e)}")
        finally:
            db.close()

        status = "success" if metadata["failed"] == 0 else "partial_success"
        if metadata["success"] == 0 and metadata["processed"] > 0:
            status = "failed"

        metadata["results"] = results
        return WorkerResult(status=status, score=score, violations=violations, metadata=metadata)
