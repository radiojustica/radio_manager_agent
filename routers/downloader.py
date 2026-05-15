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
    """Processo em background para baixar e catalogar músicas via DownloaderWorker."""
    try:
        logger.info(f"[Background] Disparando processamento de {len(queries)} downloads.")
        result = worker_manager_instance.run_cycle("DownloaderWorker", queries=queries, estilo=estilo)
        status = result.get('result', {}).get('status', 'unknown')
        logger.info(f"[Background] Processamento concluído com status: {status}")
        
        # Log detalhado de resultados
        metadata = result.get('result', {}).get('metadata', {})
        if metadata:
            logger.info(
                f"[Background] Resumo: {metadata.get('success', 0)} sucesso, "
                f"{metadata.get('failed', 0)} falhas, {metadata.get('skipped', 0)} puladas"
            )
    except Exception as e:
        logger.error(f"[Background] Falha crítica ao acionar DownloaderWorker: {e}", exc_info=True)

@router.post("/download")
async def trigger_downloads(req: DownloadRequest, background_tasks: BackgroundTasks):
    """Dispara o download das músicas selecionadas."""
    logger.info(f"Recebida requisição de download para: {req.queries}")
    background_tasks.add_task(_process_downloads, req.queries, req.estilo)
    return {"success": True, "message": f"Download de {len(req.queries)} músicas iniciado em background."}

@router.get("/progress")
async def get_download_progress():
    """Retorna o progresso atual de todos os downloads ativos."""
    from services.downloader_service import downloader_instance
    return {
        "active": downloader_instance.active_progress
    }
