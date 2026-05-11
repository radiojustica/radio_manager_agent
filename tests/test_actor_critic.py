import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from director.actor_critic import ActorCriticDirector


def test_memory_load_save(tmp_path):
    memory_path = tmp_path / "memoria_workers.json"
    director = ActorCriticDirector(memory_path=str(memory_path))

    memory = director.load_memory()
    assert memory["score_total"] == 0
    assert memory["historico_penalidades"] == []

    memory["score_total"] = 7
    memory["historico_penalidades"].append("Teste de penalidade")
    director.save_memory(memory)

    with open(memory_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["score_total"] == 7
    assert data["historico_penalidades"] == ["Teste de penalidade"]


def test_query_ollama_parses_json_array():
    director = ActorCriticDirector(memory_path="memory_dummy.json")
    tracks = [
        {"caminho": "D:\\RADIO\\MUSICAS\\A - Faixa A.mp3", "titulo": "Faixa A", "artista": "A", "estilo": "pop", "energia": 3, "duracao": 210}
    ]
    memory = {"historico_penalidades": [], "score_total": 0}

    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"response": "[\"D:\\\\RADIO\\\\MUSICAS\\\\A - Faixa A.mp3\"]"}

    with patch("director.actor_critic.requests.post", return_value=mock_response):
        selection = director.query_ollama(tracks, memory, 10, "Ensolarado")

    assert selection == ["D:\\RADIO\\MUSICAS\\A - Faixa A.mp3"]


def test_evaluate_playlist_rejects_artist_repeat():
    director = ActorCriticDirector(memory_path="memory_dummy.json")
    paths = [
        "D:\\RADIO\\MUSICAS\\ARTISTA1 - Faixa A.mp3",
        "D:\\RADIO\\MUSICAS\\ARTISTA1 - Faixa B.mp3"
    ]

    score, violations = director.evaluate_playlist(paths)

    assert score < 0
    assert violations
    assert any("Artista" in str(v) or "repite" in str(v).lower() for v in violations)
