import logging
from typing import Any
from core.worker_base import WorkerBase, WorkerResult
from core.reward import RewardStore
from scripts.report_manager import ReportManager

logger = logging.getLogger("OmniCore.Workers.ReportWorker")

class ReportWorker(WorkerBase):
    """
    Worker responsável pela geração de relatórios semanais (Audit, Performance, Playback).
    """
    def __init__(self, reward_store: RewardStore | None = None, config: dict[str, Any] | None = None):
        super().__init__(name="ReportWorker", reward_store=reward_store, config=config)
        self.manager = ReportManager()

    def run_cycle(self, **kwargs) -> WorkerResult:
        try:
            self.log_action("REPORT_GEN_START")
            results = self.manager.run_weekly_pipeline()
            
            summary = f"Relatórios gerados: {os.path.basename(results['audit'])} e {os.path.basename(results['performance'])}"
            
            return WorkerResult(
                status="success",
                score=20,
                metadata={
                    "message": summary,
                    "files": results,
                    "timestamp": results["timestamp"]
                }
            )
        except Exception as e:
            self.log_error(e, "REPORT_GEN_FAILED")
            return WorkerResult(
                status="error",
                score=-5,
                violations=[f"Falha na geração de relatórios: {str(e)}"]
            )

import os # Necessário para os.path.basename acima
