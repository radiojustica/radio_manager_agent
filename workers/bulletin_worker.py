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
        """Executa a sincronização de boletins informativos."""
        self.log_action("SYNC_START")
        
        violations = []
        metadata = {
            "bulletin_sync": {},
            "updated_count": 0
        }
        
        from core.database import SessionLocal
        from services.autopilot_service import autopilot_service
        db = SessionLocal()
        
        try:
            bulletin_res = self.syncer.sync()
            metadata["bulletin_sync"] = bulletin_res
            if not bulletin_res.get("success", False):
                err_msg = bulletin_res.get('error', 'Erro desconhecido')
                violations.append(f"Boletins: {err_msg}")
                autopilot_service.log_action(db, "SYNC_BULLETIN", f"Falha na sincronização automática de boletins: {err_msg}", success=False)
            else:
                updated = bulletin_res.get("updated", 0)
                metadata["updated_count"] += updated
                msg = f"Sincronização automática de boletins concluída. {updated} atualizações."
                autopilot_service.log_action(db, "SYNC_BULLETIN", msg, success=True)
        except Exception as e:
            self.log_error(e, "BULLETIN_SYNC_FAILED")
            violations.append(f"Boletins: {str(e)}")
            try:
                autopilot_service.log_action(db, "SYNC_BULLETIN", f"Erro crítico na sincronização automática de boletins: {str(e)}", success=False)
            except Exception as le:
                logger.error(f"Erro ao registrar log de erro no BulletinWorker: {le}")
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
            message = f"Sincronização de boletins concluída: {updated} atualizações realizadas."
        else:
            score = 2
            status = "idle"
            message = "Sincronização de boletins concluída: tudo em dia."
            
        metadata["message"] = message
        return WorkerResult(
            status=status,
            score=score,
            metadata=metadata
        )
