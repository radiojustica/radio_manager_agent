import pytest
import os
import sys
import json
from unittest.mock import MagicMock, patch

# Adiciona o diretório raiz do projeto ao sys.path para importação
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.subagent_base import SubAgentBase, tool
from core.worker_base import WorkerResult
from workers.curadoria_worker import CuradoriaWorker
from workers.playlist_worker import PlaylistWorker
from workers.downloader_worker import DownloaderWorker
from workers.daily_report_worker import DailyReportWorker

class MockSubAgent(SubAgentBase):
    def __init__(self, reward_store=None, config=None):
        super().__init__(name="MockSubAgent", reward_store=reward_store, config=config)
        self.tool_called = False
        self.tool_arg_received = None

    @tool
    def minha_ferramenta(self, arg_val: str) -> str:
        """Uma ferramenta de teste."""
        self.tool_called = True
        self.tool_arg_received = arg_val
        return f"Retorno para {arg_val}"

    def run_cycle(self, **kwargs) -> WorkerResult:
        return WorkerResult(status="success", score=10)

class TestSubAgentBase:
    def test_tool_registration(self):
        agent = MockSubAgent()
        assert "minha_ferramenta" in agent.tools
        assert agent.tools["minha_ferramenta"].is_tool is True

    @patch("core.subagent_base.SubAgentBase.query_llm")
    def test_agent_loop_success_with_tool_call(self, mock_query):
        agent = MockSubAgent()
        
        # Simula o LLM retornando uma chamada de ferramenta no primeiro passo, e a resposta final no segundo
        step1_response = json.dumps({
            "thought": "Vou chamar minha_ferramenta",
            "tool": "minha_ferramenta",
            "args": {"arg_val": "teste_arg"}
        })
        step2_response = json.dumps({
            "thought": "Terminei",
            "tool": None,
            "args": None,
            "final_answer": {"status": "success", "result": "Resultado Final da Tarefa"}
        })
        
        mock_query.side_effect = [step1_response, step2_response]
        
        result = agent.run_agent_loop("Faça algo", "Instrução de Sistema", max_steps=3)
        
        assert result.get("status") == "success"
        assert result.get("result") == "Resultado Final da Tarefa"
        assert agent.tool_called is True
        assert agent.tool_arg_received == "teste_arg"
        assert mock_query.call_count == 2

class TestConcreteSubagents:
    @patch("core.subagent_base.SubAgentBase.run_agent_loop")
    @patch("workers.curadoria_worker.SessionLocal")
    def test_curadoria_worker_cycle(self, mock_session, mock_agent_loop):
        # Configura mocks para o banco e para o loop do agente
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        
        mock_musica = MagicMock()
        mock_musica.id = 42
        mock_musica.titulo = "Música de Teste"
        mock_musica.artista = "Artista Teste"
        mock_musica.caminho = "teste.mp3"
        mock_musica.auditado_acustica = False
        mock_musica.mood = None
        mock_musica.redflag = False
        
        mock_db.query().filter().order_by().limit().all.return_value = [mock_musica]
        mock_agent_loop.return_value = {"status": "success", "result": "Curadoria concluída"}
        
        worker = CuradoriaWorker()
        res = worker.run_cycle()
        
        assert res.status == "success"
        assert res.score == 5
        assert res.metadata["processed_count"] == 1
        assert mock_agent_loop.call_count == 1

    @patch("core.subagent_base.SubAgentBase.run_agent_loop")
    def test_playlist_worker_cycle(self, mock_agent_loop):
        mock_agent_loop.return_value = {"status": "success", "result": "Playlist gravada com sucesso"}
        
        worker = PlaylistWorker()
        res = worker.run_cycle(hora_inicio=14, mood="Ensolarado")
        
        assert res.status == "success"
        assert res.score == 15
        assert res.metadata["hora_inicio"] == 14
        assert mock_agent_loop.call_count == 1

    @patch("core.subagent_base.SubAgentBase.run_agent_loop")
    def test_playlist_worker_daily_cycle(self, mock_agent_loop):
        mock_agent_loop.return_value = {"status": "success", "result": "Playlist gravada com sucesso"}
        
        worker = PlaylistWorker()
        res = worker.run_cycle(hora_inicio=None, mood="Ensolarado")
        
        assert res.status == "success"
        assert res.score == 120
        assert res.metadata["sucessos"] == 12
        assert mock_agent_loop.call_count == 12

    @patch("core.subagent_base.SubAgentBase.run_agent_loop")
    def test_downloader_worker_cycle(self, mock_agent_loop):
        mock_agent_loop.return_value = {"status": "success", "result": "Downloads concluídos"}
        
        worker = DownloaderWorker()
        res = worker.run_cycle(queries=["eminem - test"])
        
        assert res.status == "success"
        assert res.score == 5
        assert res.metadata["proactive"] is False
        assert mock_agent_loop.call_count == 1

    @patch("core.subagent_base.SubAgentBase.run_agent_loop")
    def test_daily_report_worker_cycle(self, mock_agent_loop):
        mock_agent_loop.return_value = {"status": "success", "result": "Relatório enviado via WhatsApp"}
        
        worker = DailyReportWorker()
        res = worker.run_cycle()
        
        assert res.status == "success"
        assert res.score == 10
        assert mock_agent_loop.call_count == 1
