import logging
from typing import Any
from core.worker_base import WorkerBase, WorkerResult
from scripts.omni_spider import OmniSpider

logger = logging.getLogger("OmniCore.Worker.SpiderWorker")

class SpiderWorker(WorkerBase):
    def __init__(self, reward_store: Any | None = None, config: dict[str, Any] | None = None):
        super().__init__(name="SpiderWorker", reward_store=reward_store, config=config)
        self.spider = OmniSpider()

    def run_cycle(self, **kwargs) -> WorkerResult:
        """Executa a varredura completa do OmniSpider."""
        self.log_action("SPIN_START")
        
        try:
            res = self.spider.spin()
            updated = res.get("updated_total", 0)
            
            if res.get("success"):
                return WorkerResult(
                    status="success" if updated > 0 else "idle",
                    score=5 if updated > 0 else 2,
                    metadata=res
                )
            else:
                return WorkerResult(
                    status="error",
                    score=-5,
                    violations=[res.get("error", "Erro desconhecido no Spider")],
                    metadata=res
                )
        except Exception as e:
            self.log_error(e, "SPIDER_CRASH")
            return WorkerResult(
                status="error",
                score=-10,
                violations=[str(e)],
                metadata={"error": str(e)}
            )
