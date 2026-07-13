from fastapi import APIRouter, HTTPException
from worker_manager import worker_manager_instance
from typing import List, Dict, Any

router = APIRouter(prefix="/api/workers", tags=["Workers"])

@router.get("/status")
def get_workers_status() -> List[Dict[str, Any]]:
    """Retorna o status de saúde e telemetria de todos os workers registrados."""
    return [worker.health() for worker in worker_manager_instance.workers.values()]

@router.get("/")
def list_workers() -> List[str]:
    """Lista os nomes dos workers registrados."""
    return list(worker_manager_instance.workers.keys())

@router.get("/summary")
def get_workers_summary() -> Dict[str, Any]:
    """Retorna o resumo de recompensas de todos os workers."""
    return worker_manager_instance.reward_store.summary()

@router.get("/history")
def get_workers_history(name: str | None = None, limit: int = 50) -> list[Dict[str, Any]]:
    """Retorna o histórico de execução do worker ou histórico global."""
    return worker_manager_instance.reward_store.history(worker_name=name, limit=limit)

@router.get("/history/descriptive")
def get_workers_history_descriptive(name: str | None = None, limit: int = 50) -> list[Dict[str, Any]]:
    """Retorna um histórico simplificado e descritivo das ações dos workers."""
    history = worker_manager_instance.reward_store.history(worker_name=name, limit=limit)
    return [
        {
            "timestamp": h.get("timestamp"),
            "worker": h.get("worker"),
            "description": h.get("description"),
            "score": h.get("score")
        }
        for h in history
    ]

@router.post("/content-agent/run")
def run_content_agent():
    """
    Dispara a sequência completa de produção de conteúdo:
    1. Geração de IA (ContentGenerationWorker)
    2. Sincronização de Boletins, NJUD e Giro.
    """
    if not worker_manager_instance.get_worker("ContentGenerationWorker"):
        raise HTTPException(
            status_code=403,
            detail="A geração de conteúdo por inteligência artificial foi suspensa por determinação institucional."
        )
        
    results = {}
    
    # 1. Geração de IA (Este pode demorar vários minutos)
    # Por ser síncrono no run_cycle atual, o request vai travar até terminar.
    # TODO: No futuro, tornar isso assíncrono com feedback por websocket.
    results["generation"] = worker_manager_instance.run_cycle("ContentGenerationWorker")
    
    # 2. Sincronizações (Só faz sentido se a geração teve algum sucesso ou para garantir)
    results["bulletins"] = worker_manager_instance.run_cycle("BulletinWorker")
    results["njud"] = worker_manager_instance.run_cycle("NjudWorker")
    results["giro"] = worker_manager_instance.run_cycle("GiroWorker")
    
    return {
        "success": all(r.get("result", {}).get("status") != "error" for r in results.values()),
        "details": results
    }

@router.post("/spider/run")
def run_spider_manually():
    """
    Dispara manualmente o OmniSpider para varredura total do Drive.
    """
    return worker_manager_instance.run_cycle("SpiderWorker")

@router.get("/ntfy-listener/status")
def get_ntfy_listener_status():
    """Retorna o estado atual do listener ntfy (canal radio_tjrn)."""
    try:
        from services.ntfy_listener_service import ntfy_listener_service, NTFY_CHANNEL, COMMAND_MAP
        running = ntfy_listener_service._running
        thread_alive = (
            ntfy_listener_service._thread is not None
            and ntfy_listener_service._thread.is_alive()
        )
        return {
            "running": running and thread_alive,
            "thread_alive": thread_alive,
            "channel": NTFY_CHANNEL,
            "sse_url": f"https://ntfy.sh/{NTFY_CHANNEL}/sse",
            "comandos_disponiveis": list(COMMAND_MAP.keys()),
        }
    except Exception as e:
        return {"running": False, "error": str(e)}

@router.post("/ntfy-listener/start")
def start_ntfy_listener():
    """
    Inicia o NtfyListenerService no processo atual (hot-start).
    Útil quando o sistema já estava rodando antes da feature ser deployada.
    Operação idempotente: se já estiver rodando, retorna o status sem erro.
    """
    try:
        from services.ntfy_listener_service import ntfy_listener_service, NTFY_CHANNEL, COMMAND_MAP
        if ntfy_listener_service._running and ntfy_listener_service._thread and ntfy_listener_service._thread.is_alive():
            return {
                "started": False,
                "message": "Listener já estava em execução.",
                "channel": NTFY_CHANNEL,
                "comandos_disponiveis": list(COMMAND_MAP.keys()),
            }
        ntfy_listener_service.start(worker_manager_instance)
        return {
            "started": True,
            "message": f"NtfyListenerService iniciado com sucesso no canal radio_tjrn.",
            "channel": NTFY_CHANNEL,
            "comandos_disponiveis": list(COMMAND_MAP.keys()),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao iniciar listener ntfy: {e}")

@router.post("/{name}/run")
def run_worker_manually(name: str):
    """
    Dispara manualmente um ciclo de execução para um worker específico.
    """
    worker = worker_manager_instance.get_worker(name)
    if not worker:
        raise HTTPException(status_code=404, detail=f"Worker '{name}' não encontrado no registro.")
    
    # Executa o ciclo de forma síncrona (padrão atual do sistema)
    result = worker_manager_instance.run_cycle(name)
    return result
