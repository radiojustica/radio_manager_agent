import os
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.reward import RewardStore
from core.worker_base import WorkerBase, WorkerResult
from worker_manager import WorkerManager


class DummyWorker(WorkerBase):
    def run_cycle(self, **kwargs) -> WorkerResult:
        return WorkerResult(status="success", score=2, violations=[], metadata={"dummy": True})


def test_reward_store_record_and_summary(tmp_path):
    path = tmp_path / "rewards.json"
    store = RewardStore(path)
    store.record("DummyWorker", 2, ["none"], {"step": 1})

    assert store.summary()["DummyWorker"]["score_total"] == 2
    assert store.summary()["DummyWorker"]["cycles"] == 1
    assert store.latest("DummyWorker")["last_result"]["score"] == 2
    assert path.exists()

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["history"][0]["worker"] == "DummyWorker"


def test_worker_execute_cycle_records_score(tmp_path):
    path = tmp_path / "rewards.json"
    store = RewardStore(path)
    worker = DummyWorker(name="DummyWorker", reward_store=store)
    result = worker.execute_cycle()

    assert result.status == "success"
    assert store.summary()["DummyWorker"]["score_total"] == 2
    assert store.summary()["DummyWorker"]["cycles"] == 1


def test_worker_manager_register_and_run(tmp_path):
    path = tmp_path / "rewards.json"
    manager = WorkerManager(reward_path=str(path))
    dummy = DummyWorker(name="DummyWorker", reward_store=manager.reward_store)
    manager.register_worker(dummy)

    response = manager.run_cycle("DummyWorker")
    assert response["worker"] == "DummyWorker"
    assert response["result"]["status"] == "success"
    assert response["health"]["score_total"] == 2


def test_run_cycle_unknown_worker_records_critical_failure(tmp_path):
    path = tmp_path / "rewards.json"
    manager = WorkerManager(reward_path=str(path))

    response = manager.run_cycle("UnknownWorker")
    assert response["worker"] == "UnknownWorker"
    assert response["result"]["status"] == "error"
    assert response["health"]["running"] is False
    assert manager.reward_store.summary()["UnknownWorker"]["score_total"] == -10
    assert manager.reward_store.summary()["UnknownWorker"]["cycles"] == 1


@patch("worker_manager.PlaylistWorker")
def test_manager_can_register_playlist_mock(mock_playlist_worker):
    manager = WorkerManager()
    playlist_instance = MagicMock()
    playlist_instance.name = "PlaylistWorker"
    manager.register_worker(playlist_instance)

    response = manager.run_cycle("PlaylistWorker")
    assert response["worker"] == "PlaylistWorker"


@patch("workers.butt_worker.guardian_instance")
def test_butt_worker_records_reconnects(mock_guardian_instance, tmp_path):
    path = tmp_path / "rewards.json"
    manager = WorkerManager(reward_path=str(path))
    manager.register_worker(
        __import__("workers.butt_worker", fromlist=["ButtWorker"]).ButtWorker(reward_store=manager.reward_store)
    )
    mock_guardian_instance.reconnect_idle_butts.return_value = (2, 3)

    response = manager.run_cycle("ButtWorker")
    assert response["worker"] == "ButtWorker"
    assert response["result"]["status"] == "success"
    assert response["result"]["metadata"]["reconnected"] == 2
    assert response["health"]["score_total"] == 10
