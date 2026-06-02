import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from workers.bulletin_worker import BulletinWorker
from workers.njud_worker import NjudWorker
from core.reward import RewardStore
from core.worker_base import WorkerResult

@patch("workers.bulletin_worker.BulletinSync")
def test_bulletin_worker_success(mock_bulletin_sync, tmp_path):
    # Setup
    reward_path = tmp_path / "rewards.json"
    reward_store = RewardStore(reward_path)
    worker = BulletinWorker(reward_store=reward_store)
    
    # Mockando a resposta da sincronização com 2 arquivos novos
    mock_syncer = MagicMock()
    mock_bulletin_sync.return_value = mock_syncer
    mock_syncer.sync.return_value = {
        "success": True,
        "updated": 2,
        "total_scanned": 10,
        "total_matched": 2
    }
    
    # Re-instancia para pegar o mock_syncer
    worker.syncer = mock_syncer
    
    # Execute
    res = worker.execute_cycle()
    
    # Assert
    assert res.status == "success"
    assert res.score == 5
    assert res.metadata["updated_count"] == 2
    assert "bulletin_sync" in res.metadata

@patch("workers.bulletin_worker.BulletinSync")
def test_bulletin_worker_failed(mock_bulletin_sync, tmp_path):
    # Setup
    reward_path = tmp_path / "rewards.json"
    reward_store = RewardStore(reward_path)
    worker = BulletinWorker(reward_store=reward_store)
    
    # Mockando falha de sincronização
    mock_syncer = MagicMock()
    mock_bulletin_sync.return_value = mock_syncer
    mock_syncer.sync.return_value = {
        "success": False,
        "error": "Permissão negada no Drive"
    }
    
    worker.syncer = mock_syncer
    
    # Execute
    res = worker.execute_cycle()
    
    # Assert
    assert res.status == "error"
    assert res.score == -5
    assert len(res.violations) == 1
    assert "Permissão negada" in res.violations[0]

@patch("workers.njud_worker.NjudSync")
def test_njud_worker_success(mock_njud_sync, tmp_path):
    # Setup
    reward_path = tmp_path / "rewards.json"
    reward_store = RewardStore(reward_path)
    worker = NjudWorker(reward_store=reward_store)
    
    # Mockando sucesso de sincronização com 1 arquivo
    mock_syncer = MagicMock()
    mock_njud_sync.return_value = mock_syncer
    mock_syncer.sync.return_value = {
        "success": True,
        "updated": 1,
        "total_scanned": 5,
        "total_matched": 1
    }
    
    worker.syncer = mock_syncer
    
    # Execute
    res = worker.execute_cycle()
    
    # Assert
    assert res.status == "success"
    assert res.score == 5
    assert res.metadata["updated_count"] == 1
    assert "njud_sync" in res.metadata

@patch("workers.njud_worker.NjudSync")
def test_njud_worker_idle(mock_njud_sync, tmp_path):
    # Setup
    reward_path = tmp_path / "rewards.json"
    reward_store = RewardStore(reward_path)
    worker = NjudWorker(reward_store=reward_store)
    
    # Mockando sem atualizações (idle)
    mock_syncer = MagicMock()
    mock_njud_sync.return_value = mock_syncer
    mock_syncer.sync.return_value = {
        "success": True,
        "updated": 0,
        "total_scanned": 5,
        "total_matched": 0
    }
    
    worker.syncer = mock_syncer
    
    # Execute
    res = worker.execute_cycle()
    
    # Assert
    assert res.status == "idle"
    assert res.score == 2
    assert res.metadata["updated_count"] == 0
