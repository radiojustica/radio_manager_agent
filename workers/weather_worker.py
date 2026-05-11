import logging
from typing import Any
from datetime import datetime

from core.worker_base import WorkerBase, WorkerResult
from core.reward import RewardStore
from services import weather_service

logger = logging.getLogger("OmniCore.Workers.Weather")

class WeatherWorker(WorkerBase):
    """
    Worker responsável pela sincronização do clima e definição do 'Mood' da rádio.
    """
    def __init__(self, reward_store: RewardStore | None = None, config: dict[str, Any] | None = None):
        super().__init__(name="WeatherWorker", reward_store=reward_store, config=config)

    def run_cycle(self, **kwargs) -> WorkerResult:
        try:
            mood = weather_service.get_natal_weather_mood()
            
            # Em um cenário real, poderíamos atualizar o estado global ou banco aqui
            # Por enquanto, apenas retornamos o mood como metadata e sucesso.
            
            metadata = {
                "mood": mood,
                "timestamp": datetime.now().isoformat(),
                "location": "Natal/RN"
            }
            
            return WorkerResult(status="success", score=1, metadata=metadata)
        except Exception as e:
            logger.error(f"Erro no WeatherWorker: {e}")
            return WorkerResult(status="error", score=-1, violations=[str(e)])
