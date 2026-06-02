import pytest
import os
import sys
import json
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
        self.mood = None
        self.bpm = 0
        self.valence = 0.5
        self.danceability = 0.5
        self.quarantine_reason = None
        self.artista = "Artista Teste"
        self.titulo = "Título Teste"

@patch("workers.curadoria_worker.SessionLocal")
@patch("workers.curadoria_worker.processar_arquivo")
@patch("core.subagent_base.SubAgentBase.query_llm")
def test_curadoria_worker_success(mock_query, mock_processar, mock_session, tmp_path):
    # Setup
    reward_path = tmp_path / "rewards.json"
    reward_store = RewardStore(reward_path)
    worker = CuradoriaWorker(reward_store=reward_store)
    
    db_mock = MagicMock()
    mock_session.return_value = db_mock
    
    musica = MockMusica(1, "test.mp3")
    db_mock.query().filter().order_by().limit().all.return_value = [musica]
    db_mock.query().filter().first.return_value = musica
    
    mock_processar.return_value = {
        "status": "OK",
        "energia": 4,
        "duracao": 200,
        "bpm": 120,
        "valence": 0.5,
        "danceability": 0.5
    }
    
    # Simula o ReAct loop da curadoria de sucesso
    step1_response = json.dumps({
        "thought": "Auditar acústica",
        "tool": "auditar_arquivo_acustica",
        "args": {"musica_id": 1, "caminho": "test.mp3"}
    })
    step2_response = json.dumps({
        "thought": "Salvar curadoria",
        "tool": "salvar_curadoria",
        "args": {"musica_id": 1, "mood": "Ensolarado", "energia": 4, "bpm": 120, "valence": 0.5, "danceability": 0.5}
    })
    step3_response = json.dumps({
        "thought": "Fim",
        "tool": None,
        "final_answer": {"status": "success", "result": "Música classificada"}
    })
    mock_query.side_effect = [step1_response, step2_response, step3_response]
    
    # Execute
    result = worker.execute_cycle()
    
    # Assert
    assert result.status == "success"
    assert result.score == 5
    assert result.metadata["processed_count"] == 1
    assert musica.auditado_acustica is True
    assert musica.energia == 4
    assert db_mock.commit.called

@patch("workers.curadoria_worker.SessionLocal")
@patch("workers.curadoria_worker.processar_arquivo")
@patch("core.subagent_base.SubAgentBase.query_llm")
def test_curadoria_worker_quarantine(mock_query, mock_processar, mock_session, tmp_path):
    # Setup
    reward_path = tmp_path / "rewards.json"
    reward_store = RewardStore(reward_path)
    worker = CuradoriaWorker(reward_store=reward_store)
    
    db_mock = MagicMock()
    mock_session.return_value = db_mock
    
    musica = MockMusica(2, "bad.mp3")
    db_mock.query().filter().order_by().limit().all.return_value = [musica]
    db_mock.query().filter().first.return_value = musica
    
    mock_processar.return_value = {
        "status": "QUARANTINED",
        "motivo": "Inadequação",
        "duracao": 180
    }
    
    # Simula o ReAct loop de quarentena
    step1_response = json.dumps({
        "thought": "Auditar",
        "tool": "auditar_arquivo_acustica",
        "args": {"musica_id": 2, "caminho": "bad.mp3"}
    })
    step2_response = json.dumps({
        "thought": "Quarentena",
        "tool": "enviar_quarentena",
        "args": {"musica_id": 2, "motivo": "Inadequação"}
    })
    step3_response = json.dumps({
        "thought": "Fim",
        "tool": None,
        "final_answer": {"status": "success", "result": "Música em quarentena"}
    })
    mock_query.side_effect = [step1_response, step2_response, step3_response]
    
    # Execute
    result = worker.execute_cycle()
    
    # Assert
    assert result.status == "success"
    assert result.score == 5
    assert musica.redflag is True
    assert len(result.violations) == 1
    assert "quarentena" in result.violations[0]
