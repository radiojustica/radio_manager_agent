from datetime import datetime
from typing import Any

from core.worker_base import WorkerBase, WorkerResult
from director.playlist_engine import playlist_engine_instance


class PlaylistWorker(WorkerBase):
    def __init__(self, name: str = "PlaylistWorker", reward_store=None, config: dict[str, Any] | None = None):
        super().__init__(name=name, reward_store=reward_store, config=config)

    def run_cycle(self, hora_inicio: int = 0, mood: str | None = None) -> WorkerResult:
        result = playlist_engine_instance.gerar_playlist_bloco(hora_inicio, mood)
        score = 10 if result else -5
        violations = [] if result else [f"Falha na geração do bloco {hora_inicio:02d}H"]
        metadata = {
            "hora_inicio": hora_inicio,
            "mood": mood,
            "generated_at": datetime.utcnow().isoformat(),
        }
        return WorkerResult(status="success" if result else "failed", score=score, violations=violations, metadata=metadata)
