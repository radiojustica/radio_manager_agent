import os
import logging
from typing import Any

from core.subagent_base import SubAgentBase, tool
from core.worker_base import WorkerResult
from core.reward import RewardStore
from services.downloader_service import downloader_instance
from core.database import SessionLocal
from core.models import Musica

logger = logging.getLogger("OmniCore.Workers.Downloader")

class DownloaderWorker(SubAgentBase):
    """
    Subagente de Aquisição Musical (A&R Scout).
    Procura músicas recomendadas ou sob demanda, realiza o download via YouTube/fontes
    e cataloga as faixas no acervo com validação de metadados.
    """
    def __init__(self, reward_store: RewardStore | None = None, config: dict[str, Any] | None = None):
        super().__init__(name="DownloaderWorker", reward_store=reward_store, config=config)
        self.proactive_limit = self.config.get("proactive_limit", 3)

    @tool
    def obter_recomendacoes_acervo(self) -> list:
        """
        Consulta o motor de recomendação interno para analisar os últimos 5 dias de execução
        e sugerir faixas que combinam com a programação da rádio.
        Retorna uma lista de strings contendo sugestões de busca (queries).
        """
        try:
            from director.recommender import recommender_instance
            analysis = recommender_instance.analyze_last_days(5)
            recs = recommender_instance.generate_recommendations(analysis)
            return [r["sugestao"] for r in recs[:self.proactive_limit]]
        except Exception as e:
            logger.error(f"Erro ao gerar recomendações no motor: {e}")
            return []

    @tool
    def buscar_e_baixar_faixa(self, query: str) -> dict:
        """
        Busca e executa o download físico da música a partir do YouTube/fontes externas baseando-se na query.
        Retorna um dicionário com os campos 'success', 'path', 'title', 'skipped' ou 'error'.
        """
        try:
            res = downloader_instance.search_and_download(query)
            return res
        except TimeoutError as e:
            return {"success": False, "error": f"Timeout: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @tool
    def cadastrar_musica(self, caminho: str, artista: str, titulo: str, estilo: str) -> str:
        """
        Cadastra a música baixada com sucesso no banco de dados SQLite da rádio, evitando duplicações.
        """
        db = SessionLocal()
        try:
            # Verifica duplicidade no banco
            musica_existente = db.query(Musica).filter(Musica.caminho == caminho).first()
            if musica_existente:
                return f"Música já presente no banco de dados (ID: {musica_existente.id})."
            
            nova_musica = Musica(
                caminho=caminho,
                artista=artista.strip().upper(),
                titulo=titulo.strip(),
                estilo=estilo.lower(),
                auditado_acustica=False
            )
            db.add(nova_musica)
            db.commit()
            return f"Música '{artista} - {titulo}' cadastrada com sucesso com ID {nova_musica.id}."
        except Exception as e:
            db.rollback()
            return f"Erro ao cadastrar música no banco: {e}"
        finally:
            db.close()

    def run_cycle(self, queries: list[str] | None = None, estilo: str = "outros", **kwargs) -> WorkerResult:
        is_proactive = queries is None
        self.log_action("DOWNLOAD_CYCLE_START", proactive=is_proactive)
        
        system_prompt = (
            "Você é o Subagente de Aquisição Musical (A&R Scout) do Omni Core V2.\n"
            "Seu trabalho é encontrar novas músicas que complementam a programação, baixá-las e registrá-las no banco.\n"
            "Instruções:\n"
            "1. Se nenhuma query/música específica for fornecida, use a ferramenta 'obter_recomendacoes_acervo' para descobrir sugestões automáticas.\n"
            "2. Para cada sugestão/query, chame a ferramenta 'buscar_e_baixar_faixa'.\n"
            "3. Se o download for um sucesso, extraia o Artista e o Título de forma limpa.\n"
            "   (Ex: se o título do vídeo for 'Eminem - Without Me', Artista='EMINEM', Título='Without Me').\n"
            "4. Chame a ferramenta 'cadastrar_musica' para persistir a nova música no banco de dados.\n"
            "5. Finalize reportando o resumo dos downloads executados."
        )

        task = f"Executar ciclo de download. Proativo: {is_proactive}. Queries fornecidas: {queries}. Estilo alvo: {estilo}"

        try:
            # Configura um parâmetro dinâmico nas ferramentas para simplificar
            self.register_tool_func("cadastrar_musica", lambda caminho, artista, titulo: self.cadastrar_musica(caminho, artista, titulo, estilo))
            
            res = self.run_agent_loop(task, system_prompt, max_steps=6)
            
            if res.get("status") == "success":
                score = 10 if is_proactive else 5
                return WorkerResult(status="success", score=score, metadata={"result": res.get("result"), "proactive": is_proactive})
            else:
                return WorkerResult(
                    status="failed", 
                    score=-5, 
                    violations=[f"Subagente falhou no loop de download: {res.get('result')}"],
                    metadata={"proactive": is_proactive}
                )
        except Exception as e:
            logger.error(f"Erro no ciclo do DownloaderWorker: {e}")
            return WorkerResult(status="error", score=-10, violations=[str(e)])
