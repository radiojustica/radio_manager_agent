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
        
        from core.database import SessionLocal
        from services.autopilot_service import autopilot_service
        db = SessionLocal()
        
        try:
            njud_res = self.syncer.sync()
            metadata["njud_sync"] = njud_res
            if not njud_res.get("success", False):
                err_msg = njud_res.get('error', 'Erro desconhecido')
                violations.append(f"NJUD: {err_msg}")
                autopilot_service.log_action(db, "SYNC_NJUD", f"Falha na sincronização automática de jornais (NJUD): {err_msg}", success=False)
            else:
                updated = njud_res.get("updated", 0)
                metadata["updated_count"] += updated
                msg = f"Sincronização automática do NJUD (Jornais) concluída. {updated} atualizações."
                autopilot_service.log_action(db, "SYNC_NJUD", msg, success=True)
        except Exception as e:
            self.log_error(e, "NJUD_SYNC_FAILED")
            violations.append(f"NJUD: {str(e)}")
            try:
                autopilot_service.log_action(db, "SYNC_NJUD", f"Erro crítico na sincronização automática de jornais (NJUD): {str(e)}", success=False)
            except Exception as le:
                logger.error(f"Erro ao registrar log de erro no NjudWorker: {le}")
        finally:
            db.close()

         # Corrigido indentação
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
