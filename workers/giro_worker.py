import logging
from typing import Any
from core.worker_base import WorkerBase, WorkerResult
from scripts.giro_sync import GiroSync

logger = logging.getLogger("OmniCore.Worker.GiroWorker")

class GiroWorker(WorkerBase):
    def __init__(self, reward_store: Any | None = None, config: dict[str, Any] | None = None):
        super().__init__(name="GiroWorker", reward_store=reward_store, config=config)
        self.syncer = GiroSync()

    def run_cycle(self, **kwargs) -> WorkerResult:
        """Executa a sincronização do Giro nas Comarcas."""
        self.log_action("SYNC_START")
        
        violations = []
        metadata = {
            "giro_sync": {},
            "updated_count": 0
        }
        
        from core.database import SessionLocal
        from services.autopilot_service import autopilot_service
        db = SessionLocal()
        
        try:
            giro_res = self.syncer.sync()
            metadata["giro_sync"] = giro_res
            if not giro_res.get("success", False):
                err_msg = giro_res.get('error', 'Erro desconhecido')
                violations.append(f"Giro nas Comarcas: {err_msg}")
                autopilot_service.log_action(db, "SYNC_GIRO", f"Falha na sincronização automática do Giro: {err_msg}", success=False)
            else:
                updated = giro_res.get("updated", 0)
                metadata["updated_count"] += updated
                msg = f"Sincronização automática do Giro nas Comarcas concluída. {updated} atualizações."
                autopilot_service.log_action(db, "SYNC_GIRO", msg, success=True)
        except Exception as e:
            self.log_error(e, "GIRO_SYNC_FAILED")
            violations.append(f"Giro nas Comarcas: {str(e)}")
            try:
                autopilot_service.log_action(db, "SYNC_GIRO", f"Erro crítico na sincronização do Giro nas Comarcas: {str(e)}", success=False)
            except Exception as le:
                logger.error(f"Erro ao registrar log de erro no GiroWorker: {le}")
        finally:
            db.close()

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
            message = f"Sincronização do Giro nas Comarcas concluída: {updated} atualizações realizadas."
        else:
            score = 2
            status = "idle"
            message = "Sincronização do Giro nas Comarcas concluída: tudo em dia."
            
        metadata["message"] = message
        return WorkerResult(
            status=status,
            score=score,
            metadata=metadata
        )
