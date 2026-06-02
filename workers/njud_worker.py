import logging
from typing import Any
from core.worker_base import WorkerBase, WorkerResult
from scripts.njud_sync import NjudSync

logger = logging.getLogger("OmniCore.Worker.NjudWorker")

class NjudWorker(WorkerBase):
    def __init__(self, reward_store: Any | None = None, config: dict[str, Any] | None = None):
        super().__init__(name="NjudWorker", reward_store=reward_store, config=config)
        self.syncer = NjudSync()

    def run_cycle(self, **kwargs) -> WorkerResult:
        """Executa a sincronização do Notícias do Judiciário (NJUD)."""
        self.log_action("SYNC_START")
        
        violations = []
        metadata = {
            "njud_sync": {},
            "updated_count": 0
        }
        
        try:
            njud_res = self.syncer.sync()
            metadata["njud_sync"] = njud_res
            if not njud_res.get("success", False):
                violations.append(f"NJUD: {njud_res.get('error', 'Erro desconhecido')}")
            else:
                metadata["updated_count"] += njud_res.get("updated", 0)
        except Exception as e:
            self.log_error(e, "NJUD_SYNC_FAILED")
            violations.append(f"NJUD: {str(e)}")

        if violations:
            return WorkerResult(
                status="error",
                score=-5,
                violations=violations,
                metadata=metadata
            )
            
        updated = metadata["updated_count"]
        if updated > 0:
            score = 5
            status = "success"
            message = f"Sincronização do NJUD concluída: {updated} atualizações realizadas."
        else:
            score = 2
            status = "idle"
            message = "Sincronização do NJUD concluída: tudo em dia."
            
        metadata["message"] = message
        return WorkerResult(
            status=status,
            score=score,
            metadata=metadata
        )
