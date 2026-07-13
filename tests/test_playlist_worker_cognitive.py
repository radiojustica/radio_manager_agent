import pytest
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from workers.playlist_worker import PlaylistWorker
from director.playlist_engine import PlaylistEngine

def test_obter_informacoes_contexto():
    worker = PlaylistWorker()
    context = worker.obter_informacoes_contexto(14)
    
    assert "clima_mood_natal" in context
    assert context["hora_bloco"] == 14
    assert "mes_atual" in context
    assert "dia_semana" in context
    assert "energia_sugerida" in context
    assert "moods_estilos_default" in context
    assert isinstance(context["moods_estilos_default"], dict)

@patch('director.playlist_engine.PlaylistEngine.gerar_playlist_bloco')
def test_gerar_playlist_via_motor_customizado(mock_gerar):
    mock_gerar.return_value = True
    worker = PlaylistWorker()
    
    res = worker.gerar_playlist_via_motor(14, mood="Nublado", estilos=["reggae", "indie"])
    
    # Verifica se o motor foi chamado com estilos customizados
    mock_gerar.assert_called_once_with(14, "Nublado", estilos_customizados=["reggae", "indie"])
    assert "Sucesso" in res
