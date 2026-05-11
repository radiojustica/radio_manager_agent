import logging
from typing import Any
from datetime import datetime

from core.worker_base import WorkerBase, WorkerResult
from core.reward import RewardStore
from director.actor_critic import actor_critic_instance

logger = logging.getLogger("OmniCore.Workers.ActorCritic")

class ActorCriticWorker(WorkerBase):
    """
    Worker que utiliza o motor Actor-Critic (IA) para gerar e avaliar playlists.
    """
    def __init__(self, reward_store: RewardStore | None = None, config: dict[str, Any] | None = None):
        super().__init__(name="ActorCriticWorker", reward_store=reward_store, config=config)

    def run_cycle(self, hora_inicio: int | None = None, mood: str | None = None, output_path: str | None = None, **kwargs) -> WorkerResult:
        if hora_inicio is None:
            hora_inicio = datetime.now().hour

        try:
            # actor_critic_instance.run_cycle já faz a avaliação e salva na memória interna dele.
            # Aqui estamos apenas integrando ao WorkerManager para auditoria centralizada.
            success = actor_critic_instance.run_cycle(hora_inicio, mood, output_path)
            
            summary = actor_critic_instance.memory_summary()
            score = 10 if success else -5
            violations = []
            if not success:
                violations.append("Falha na geração ou playlist reprovada pelo crítico.")
            
            metadata = {
                "hora_inicio": hora_inicio,
                "mood": mood,
                "score_ia": summary.get("score_total", 0),
                "historico": summary.get("historico_penalidades", [])[-3:]
            }
            
            status = "success" if success else "failed"
            return WorkerResult(status=status, score=score, violations=violations, metadata=metadata)
            
        except Exception as e:
            logger.error(f"Erro no ActorCriticWorker: {e}")
            return WorkerResult(status="error", score=-10, violations=[str(e)])
