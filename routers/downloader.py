from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import List
from director.recommender import recommender_instance
from worker_manager import worker_manager_instance
import logging

router = APIRouter(prefix="/api/downloader", tags=["Downloader"])
logger = logging.getLogger("OmniCore.DownloaderAPI")

class DownloadRequest(BaseModel):
    queries: list[str] # Lista de termos de busca ou links
    estilo: str = "outros"

@router.get("/recommendations")
async def get_recommendations(days: int = 5):
    """Analisa logs e retorna sugestões de músicas para baixar."""
    try:
        analysis = recommender_instance.analyze_last_days(days)
        recs = recommender_instance.generate_recommendations(analysis)
        return {
            "success": True,
            "analysis": analysis,
            "recommendations": recs
        }
    except Exception as e:
        logger.error(f"Erro ao gerar recomendações: {e}")
        return {"success": False, "error": str(e)}

def _process_downloads(queries: list[str], estilo: str):
    """
    Processa os downloads em background chamando o serviço real de download
    (yt-dlp) DIRETAMENTE — sem depender do subagente de IA, que pode estar
    indisponível (ex.: API de LLM bloqueada). Isso garante que a fila de
    processamento e o histórico reflitam o estado real das transferências.
    """
    try:
        from services.downloader_service import downloader_instance
        logger.info(f"[Background] Processando {len(queries)} downloads (download direto).")
        resultados = []
        for q in queries:
            try:
                res = downloader_instance.search_and_download(q, destination=None)
                resultados.append({"query": q, "result": res})
            except Exception as e:
                logger.error(f"[Background] Erro ao baixar '{q}': {e}")
                resultados.append({"query": q, "result": {"success": False, "error": str(e)}})
        ok = sum(1 for r in resultados if r["result"].get("success"))
        falhas = len(resultados) - ok
        logger.info(f"[Background] Download concluído: {ok} ok, {falhas} falhas.")
    except Exception as e:
        logger.error(f"[Background] Falha crítica ao acionar downloads: {e}", exc_info=True)

@router.post("/download")
async def trigger_downloads(req: DownloadRequest, background_tasks: BackgroundTasks):
    """Dispara o download das músicas selecionadas."""
    logger.info(f"Recebida requisição de download para: {req.queries}")
    background_tasks.add_task(_process_downloads, req.queries, req.estilo)
    return {"success": True, "message": f"Download de {len(req.queries)} músicas iniciado em background."}

@router.get("/progress")
async def get_download_progress():
    """Retorna o progresso atual de downloads ativos E o histórico durável."""
    from services.downloader_service import downloader_instance
    return {
        "active": downloader_instance.active_progress,
        "history": downloader_instance.history,
    }
