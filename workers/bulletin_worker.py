import logging
from typing import Any
from core.worker_base import WorkerBase, WorkerResult
from scripts.bulletin_sync import BulletinSync

logger = logging.getLogger("OmniCore.Worker.BulletinWorker")

class BulletinWorker(WorkerBase):
    def __init__(self, reward_store: Any | None = None, config: dict[str, Any] | None = None):
        super().__init__(name="BulletinWorker", reward_store=reward_store, config=config)
        self.syncer = BulletinSync()

    def run_cycle(self, **kwargs) -> WorkerResult:
        """Executa a sincronização de boletins."""
        self.log_action("SYNC_START")
        
        try:
            result = self.syncer.sync()
            
            if not result.get("success", False):
                return WorkerResult(
                    status="error",
                    score=-5,
                    violations=[result.get("error", "Erro desconhecido na sincronização")],
                    metadata=result
                )
            
            updated_count = result.get("updated", 0)
            if updated_count > 0:
                score = 5
                status = "success"
                message = f"Sincronizado com sucesso: {updated_count} dias atualizados."
            else:
                score = 2
                status = "idle"
                message = "Sincronização concluída: tudo em dia."
            
            return WorkerResult(
                status=status,
                score=score,
                metadata={
                    "message": message,
                    "updated_count": updated_count,
                    "total_scanned": result.get("total_scanned", 0),
                    "total_matched": result.get("total_matched", 0)
                }
            )

        except Exception as e:
            self.log_error(e, "SYNC_CRITICAL_FAILURE")
            return WorkerResult(
                status="error",
                score=-5,
                violations=[f"Critical Exception: {str(e)}"],
                metadata={"exception": type(e).__name__}
            )
