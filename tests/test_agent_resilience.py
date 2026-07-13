# tests/test_agent_resilience.py
import os
import sys
import pytest
import tempfile
from datetime import datetime
from unittest.mock import patch, MagicMock

# Adiciona o diretório raiz do projeto ao sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.compliance_validator import compliance_validator_instance
from workers.playlist_worker import PlaylistWorker
from core.models import Musica
from core.database import SessionLocal

@pytest.fixture
def clean_db():
    db = SessionLocal()
    # Adiciona algumas músicas de teste no DB real para os testes funcionarem com o bancoSQLite real do ambiente
    m_regional = db.query(Musica).filter(Musica.caminho.contains("REGIONAL")).first()
    if not m_regional:
        # Se não houver, criamos uma regional temporária
        m_regional = Musica(
            caminho=r"D:\RADIO\MUSICAS\REGIONAL\luiz_gonzaga_teste.mp3",
            artista="Luiz Gonzaga",
            titulo="Luiz Gonzaga Regional Teste",
            estilo="forro",
            energia=4,
            duracao=200,
            tema_especial="junho"
        )
        db.add(m_regional)
        db.commit()
    db.close()
    yield
    # Limpeza não necessária pois o DB é persistente e músicas de teste são seguras

def test_agente_programador_timeout_fallback(clean_db):
    """Garante que se o loop do agente LLM falhar ou der timeout, o fallback determinístico cria a playlist."""
    worker = PlaylistWorker()
    
    # Moca o run_agent_loop para simular uma falha (ex: timeout da API de LLM)
    with patch.object(worker, "run_agent_loop", return_value={"status": "failed", "result": "Timeout da API Ollama"}):
        # Moca também a escrita física para não bagunçar o disco de produção
        with patch("director.playlist_engine.PlaylistEngine._escrever_m3u", return_value=True) as mock_escrever:
            with patch("core.compliance_validator.compliance_validator_instance.validate_playlist", return_value=[]):
                res = worker._gerar_bloco_unico(hora_inicio=10, mood="Ensolarado")
                
                # Deve retornar sucesso devido ao fallback determinístico
                assert res["status"] == "success"
                assert "fallback" in res["result"].lower()
                assert mock_escrever.call_count == 1

def test_violacao_conformidade_rejeitada():
    """Valida que o ComplianceValidator rejeita playlists fora dos limites regulamentares."""
    validator = compliance_validator_instance
    
    # 1. Caso: Playlist com música natalina em Junho
    with tempfile.NamedTemporaryFile("w", encoding="cp1252", delete=False, suffix=".m3u") as tmp:
        tmp.write("#EXTM3U\n")
        # Inserimos caminhos simulados
        tmp.write(r"D:\RADIO\MUSICAS\ESPECIAL_NATAL\noite_feliz.mp3" + "\n")
        tmp_path = tmp.name
        
    try:
        # Executa validação em Junho (Mês 6)
        date_context = datetime(2026, 6, 24)
        violations = validator.validate_playlist(tmp_path, hour=10, date_context=date_context)
        
        # Deve encontrar violações (natalina fora de dezembro e duração muito curta)
        assert len(violations) > 0
        assert any("natalina" in v for v in violations)
        assert any("Duração total" in v for v in violations)
    finally:
        os.unlink(tmp_path)

def test_duracao_bloco_invalida():
    """Playlist com duração inferior a 2h (7200s) ou superior a 8000s deve ser rejeitada."""
    validator = compliance_validator_instance
    
    with tempfile.NamedTemporaryFile("w", encoding="cp1252", delete=False, suffix=".m3u") as tmp:
        tmp.write("#EXTM3U\n")
        # Apenas uma música de 3 minutos e pouco
        tmp.write(r"D:\RADIO\MUSICAS\MPB\caetano.mp3" + "\n")
        tmp_path = tmp.name
        
    try:
        violations = validator.validate_playlist(tmp_path, hour=10)
        assert any("Duração total" in v for v in violations)
    finally:
        os.unlink(tmp_path)
