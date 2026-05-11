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
