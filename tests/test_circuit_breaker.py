import os
import sys
import time
from datetime import datetime, UTC, timedelta
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.reward import RewardStore
from core.worker_base import WorkerBase, WorkerResult

class FailingDummyWorker(WorkerBase):
    def __init__(self, name, should_fail=True, **kwargs):
        super().__init__(name, **kwargs)
        self.should_fail = should_fail
        self.run_count = 0

    def run_cycle(self, **kwargs) -> WorkerResult:
        self.run_count += 1
        if self.should_fail:
            raise RuntimeError("Incompetência artificial simulada do Pickle Rick!")
        return WorkerResult(status="success", score=2, violations=[], metadata={"ok": True})

def test_circuit_breaker_flow(tmp_path):
    path = tmp_path / "rewards.json"
    store = RewardStore(path)
    
    # Configura o worker para abrir o circuito após 2 falhas, com cooldown de 1 segundo
    config = {
        "circuit_breaker_max_failures": 2,
        "circuit_breaker_cooldown": 1
    }
    
    worker = FailingDummyWorker(name="FailingWorker", should_fail=True, reward_store=store, config=config)
    
    # 1. Primeira falha
    res1 = worker.execute_cycle()
    assert res1.status == "error"
    assert worker.failure_count == 1
    assert worker.circuit_open is False
    
    # 2. Segunda falha consecutive -> deve desarmar o circuito (trip)
    res2 = worker.execute_cycle()
    assert res2.status == "error"
    assert worker.failure_count == 2
    assert worker.circuit_open is True
    assert worker.circuit_open_time is not None
    
    # 3. Execuções adicionais rápidas devem ser bloqueadas imediatamente sem chamar run_cycle
    assert worker.run_count == 2  # run_cycle não deve ter sido chamado mais que 2 vezes
    res3 = worker.execute_cycle()
    assert res3.status == "circuit_breaker_open"
    assert worker.run_count == 2  # run_cycle não foi chamado
    
    # 4. Espera passar o cooldown (1 segundo)
    time.sleep(1.1)
    
    # 5. Tentativa em estado HALF-OPEN. Vamos fazê-lo ter sucesso
    worker.should_fail = False
    res4 = worker.execute_cycle()
    assert res4.status == "success"
    assert worker.run_count == 3  # run_cycle foi chamado
    assert worker.circuit_open is False
    assert worker.failure_count == 0
    assert worker.circuit_open_time is None
