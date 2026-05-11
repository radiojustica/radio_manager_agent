from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, UTC
from typing import Any

from core.reward import RewardStore

logger = logging.getLogger("OmniCore.Worker")


class WorkerResult:
    def __init__(self, status: str, score: int, violations: list[str] | None = None, metadata: dict[str, Any] | None = None):
        self.status = status
        self.score = score
        self.violations = violations or []
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "score": self.score,
            "violations": self.violations,
            "metadata": self.metadata,
        }


class WorkerBase(ABC):
    def __init__(self, name: str, reward_store: RewardStore | None = None, config: dict[str, Any] | None = None):
        self.name = name
        self.reward_store = reward_store or RewardStore()
        self.config = config or {}
        self.last_run: datetime | None = None
        self.running = False
        self.worker_logger = logging.getLogger(f"OmniCore.Worker.{name}")

    def log_action(self, action: str, level: str = "info", **kwargs) -> None:
        """Registra uma ação do worker com contexto estruturado."""
        log_data = {
            "worker": self.name,
            "action": action,
            "timestamp": datetime.now(UTC).isoformat(),
            **kwargs
        }

        message = f"[{self.name}] {action}"
        if kwargs:
            message += f" | {kwargs}"

        if level == "debug":
            self.worker_logger.debug(message, extra=log_data)
        elif level == "info":
            self.worker_logger.info(message, extra=log_data)
        elif level == "warning":
            self.worker_logger.warning(message, extra=log_data)
        elif level == "error":
            self.worker_logger.error(message, extra=log_data)
        elif level == "critical":
            self.worker_logger.critical(message, extra=log_data)

    def log_error(self, error: Exception, context: str = "", **kwargs) -> None:
        """Registra um erro com contexto completo."""
        error_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            **kwargs
        }
        self.log_action("ERROR", level="error", **error_data)

    @abstractmethod
    def run_cycle(self, **kwargs) -> WorkerResult:
        """Executa um ciclo de trabalho para o worker."""
        raise NotImplementedError

    def execute_cycle(self, **kwargs) -> WorkerResult:
        """Executa um ciclo completo com logging e reward tracking."""
        cycle_id = f"{self.name}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S_%f')}"

        self.log_action("CYCLE_START", cycle_id=cycle_id, kwargs=kwargs)
        self.running = True
        self.last_run = datetime.now(UTC)

        try:
            result = self.run_cycle(**kwargs)
            self.log_action(
                "CYCLE_SUCCESS",
                cycle_id=cycle_id,
                status=result.status,
                score=result.score,
                violations_count=len(result.violations),
                metadata=result.metadata
            )

            # Log detalhado de violações se houver
            if result.violations:
                for i, violation in enumerate(result.violations):
                    self.log_action(
                        "VIOLATION",
                        cycle_id=cycle_id,
                        violation_index=i,
                        violation_text=violation
                    )

        except Exception as e:
            self.log_error(e, "CYCLE_FAILED", cycle_id=cycle_id)
            result = WorkerResult(
                status="error",
                score=-5,
                violations=[f"Exception: {str(e)}"],
                metadata={"exception": type(e).__name__, "cycle_id": cycle_id}
            )

        # Registra no reward store
        try:
            self.reward_store.record(
                worker_name=self.name,
                score=result.score,
                violations=result.violations,
                metadata={**result.metadata, "cycle_id": cycle_id}
            )
            self.log_action("REWARD_RECORDED", cycle_id=cycle_id, score=result.score)
        except Exception as e:
            self.log_error(e, "REWARD_RECORD_FAILED", cycle_id=cycle_id)

        self.running = False
        self.log_action("CYCLE_END", cycle_id=cycle_id, final_status=result.status)
        return result

    def health(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "running": self.running,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "score_total": self.reward_store.summary().get(self.name, {}).get("score_total", 0),
        }
