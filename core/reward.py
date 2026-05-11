from __future__ import annotations

import json
import logging
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

logger = logging.getLogger("OmniCore.Reward")

DEFAULT_REWARD_STORE_PATH = Path(__file__).resolve().parent.parent / "worker_rewards.json"


class RewardStore:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path is not None else DEFAULT_REWARD_STORE_PATH
        self.reward_logger = logging.getLogger("OmniCore.Reward.Store")
        self.data = self._load()

    def _load(self) -> dict[str, Any]:
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                if isinstance(payload, dict):
                    self.reward_logger.info(f"Reward store carregado de {self.path}")
                    return payload
            except Exception as e:
                self.reward_logger.error(f"Falha ao carregar reward store: {e}")
        self.reward_logger.info(f"Reward store inicializado vazio em {self.path}")
        return {"workers": {}, "history": []}

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
            self.reward_logger.debug(f"Reward store salvo em {self.path}")
        except Exception as e:
            self.reward_logger.error(f"Falha ao salvar reward store: {e}")

    def record(self, worker_name: str, score: int, violations: list[str] | None = None, metadata: dict[str, Any] | None = None) -> None:
        violations = violations or []
        metadata = metadata or {}
        timestamp = datetime.now(UTC).isoformat()
        
        record = {
            "worker": worker_name,
            "timestamp": timestamp,
            "score": score,
            "violations": violations,
            "metadata": metadata,
        }

        # Atualiza dados do worker
        self.data.setdefault("workers", {})
        self.data["workers"].setdefault(worker_name, {"score_total": 0, "cycles": 0, "last_result": None, "history": []})

        worker_data = self.data["workers"][worker_name]
        worker_data["score_total"] += score
        worker_data["cycles"] += 1
        worker_data["last_result"] = {"score": score, "violations": violations, "metadata": metadata, "timestamp": timestamp}
        
        # Histórico persistente por worker (rolling log de 20 entradas)
        worker_data["history"] = (worker_data.get("history", []) + [record])[-20:]

        # Histórico global limitado (últimas 1000 entradas)
        self.data["history"] = (self.data.get("history", []) + [record])[-1000:]

        self.save()
        
        self.reward_logger.info(
            f"[{worker_name}] Reward recorded: score={score}, total={worker_data['score_total']}",
            extra={"worker": worker_name, "score": score, "total": worker_data["score_total"], "timestamp": timestamp}
        )

    def summary(self) -> dict[str, Any]:
        """Retorna resumo dos scores de todos os workers."""
        return self.data.get("workers", {})

    def latest(self, worker_name: str) -> dict[str, Any] | None:
        """Retorna o último resultado de um worker específico."""
        return self.data.get("workers", {}).get(worker_name)

    def history(self, worker_name: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        """Retorna histórico de rewards, opcionalmente filtrado por worker."""
        if worker_name:
            worker_data = self.data.get("workers", {}).get(worker_name, {})
            # Tenta usar o histórico persistente por worker (rolling log)
            if "history" in worker_data:
                return worker_data["history"][-limit:]
            # Fallback para scan global (migração)
            return [h for h in self.data.get("history", []) if h.get("worker") == worker_name][-limit:]
        
        return self.data.get("history", [])[-limit:]
