import pytest
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from workers.curadoria_worker import CuradoriaWorker
from core.reward import RewardStore

class MockMusica:
    def __init__(self, id, caminho):
        self.id = id
        self.caminho = caminho
        self.auditado_acustica = False
        self.duracao = 0
        self.redflag = False
        self.energia = 3

@patch("core.database.SessionLocal")
@patch("workers.curadoria_worker.processar_arquivo")
def test_curadoria_worker_success(mock_processar, mock_session, tmp_path):
    # Setup
    reward_path = tmp_path / "rewards.json"
    reward_store = RewardStore(reward_path)
    worker = CuradoriaWorker(reward_store=reward_store)
    
    db_mock = MagicMock()
    mock_session.return_value = db_mock
    
    musica = MockMusica(1, "test.mp3")
    db_mock.query().filter().order_by().limit().all.return_value = [musica]
    
    mock_processar.return_value = {
        "status": "OK",
        "energia": 4,
        "duracao": 200
    }
    
    # Execute
    result = worker.execute_cycle()
    
    # Assert
    assert result.status == "success"
    assert result.score == 2
    assert result.metadata["processed_count"] == 1
    assert musica.auditado_acustica is True
    assert musica.energia == 4
    assert db_mock.commit.called

@patch("core.database.SessionLocal")
@patch("workers.curadoria_worker.processar_arquivo")
def test_curadoria_worker_quarantine(mock_processar, mock_session, tmp_path):
    # Setup
    reward_path = tmp_path / "rewards.json"
    reward_store = RewardStore(reward_path)
    worker = CuradoriaWorker(reward_store=reward_store)
    
    db_mock = MagicMock()
    mock_session.return_value = db_mock
    
    musica = MockMusica(2, "bad.mp3")
    db_mock.query().filter().order_by().limit().all.return_value = [musica]
    
    mock_processar.return_value = {
        "status": "QUARANTINED",
        "motivo": "Inadequação",
        "duracao": 180
    }
    
    # Execute
    result = worker.execute_cycle()
    
    # Assert
    assert result.status == "success"
    assert result.score == 5
    assert musica.redflag is True
    assert len(result.violations) == 1
    assert "quarentena" in result.violations[0]
