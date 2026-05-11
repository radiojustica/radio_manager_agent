from typing import Any

from core.worker_base import WorkerBase, WorkerResult
from services.guardian_service import guardian_instance


class ButtWorker(WorkerBase):
    def __init__(self, reward_store=None, config: dict[str, Any] | None = None):
        super().__init__(name="ButtWorker", reward_store=reward_store, config=config)
        self.interval_minutes = self.config.get("interval_minutes", 2)

    def run_cycle(self, **kwargs) -> WorkerResult:
        try:
            reconectados, total = guardian_instance.reconnect_idle_butts()
            metadata = {
                "reconnected": reconectados,
                "total_instances": total,
            }

            if total == 0:
                status = "idle"
                score = 0
                violations = ["Nenhuma instância BUTT detectada"]
            elif reconectados > 0:
                status = "success"
                score = 10
                violations = []
            else:
                status = "warning"
                score = 1
                violations = ["Nenhuma instância BUTT reconectada"]

            return WorkerResult(status=status, score=score, violations=violations, metadata=metadata)
        except Exception as e:
            return WorkerResult(
                status="error",
                score=-5,
                violations=[f"Exception: {str(e)}"],
                metadata={"exception": type(e).__name__, "message": str(e)}
            )
