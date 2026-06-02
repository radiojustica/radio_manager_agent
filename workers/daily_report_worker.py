import logging
from typing import Any

from core.subagent_base import SubAgentBase, tool
from core.worker_base import WorkerResult
from core.reward import RewardStore
from services.notification_service import send_whatsapp_alert

logger = logging.getLogger("OmniCore.Workers.DailyReport")

class DailyReportWorker(SubAgentBase):
    """
    Subagente de Relatórios Diários (Reporter Agent).
    Coleta o histórico de recompensas e violações do RewardStore, analisa falhas sistêmicas,
    escreve um relatório gerencial rico em insights e despacha via WhatsApp.
    """
    def __init__(self, reward_store: RewardStore | None = None, config: dict[str, Any] | None = None):
        super().__init__(name="DailyReportWorker", reward_store=reward_store, config=config)

    @tool
    def obter_resumo_performance(self) -> dict:
        """
        Consulta a store de recompensas para obter o resumo consolidado de ciclos,
        pontuação total e violações de todos os workers registrados no Omni Core V2.
        Retorna um dicionário com estatísticas por worker.
        """
        try:
            return self.reward_store.summary()
        except Exception as e:
            logger.error(f"Erro ao ler sumário de recompensas: {e}")
            return {}

    @tool
    def enviar_relatorio_gerencial(self, texto: str) -> str:
        """
        Envia o relatório executivo final para os administradores da rádio através do WhatsApp.
        Retorna uma mensagem de confirmação.
        """
        try:
            send_whatsapp_alert(texto)
            return "Relatório gerencial enviado com sucesso via WhatsApp."
        except Exception as e:
            return f"Erro ao enviar WhatsApp: {e}"

    def run_cycle(self, **kwargs) -> WorkerResult:
        self.log_action("DAILY_REPORT_START")
        
        system_prompt = (
            "Você é o Subagente de Relatórios Executivos (Reporter Agent) do Omni Core V2.\n"
            "Seu trabalho é consolidar as métricas de todos os workers e produzir um relatório gerencial analítico.\n"
            "Instruções:\n"
            "1. Chame a ferramenta 'obter_resumo_performance' para ler os dados agregados dos workers.\n"
            "2. Analise os resultados: identifique qual worker foi mais eficiente, se houve violações críticas\n"
            "   (especialmente no GuardianWorker) e qual a eficiência global do sistema.\n"
            "3. Redija um relatório detalhado em Português do Brasil com o seguinte formato:\n"
            "   - Título marcante com Emojis (ex: 📊 *RELATÓRIO GERENCIAL - OMNI CORE V2*)\n"
            "   - Seção contendo o detalhe de pontos e ciclos por worker\n"
            "   - Resumo executivo de eficiência (Alta se pontuação geral > 0, Crítica se menor)\n"
            "   - Recomendações ou observações de saúde baseadas nos dados coletados\n"
            "4. Envie o relatório final chamando a ferramenta 'enviar_relatorio_gerencial'."
        )

        task = "Consolidar o histórico diário de execução e enviar o relatório gerencial via WhatsApp."

        try:
            res = self.run_agent_loop(task, system_prompt, max_steps=5)
            
            if res.get("status") == "success":
                return WorkerResult(
                    status="success",
                    score=10,
                    metadata={"agent_log": res.get("result")}
                )
            else:
                return WorkerResult(
                    status="failed",
                    score=-5,
                    violations=[f"Subagente falhou em gerar o relatório: {res.get('result')}"]
                )
        except Exception as e:
            logger.error(f"Erro crítico no DailyReportWorker: {e}")
            return WorkerResult(status="error", score=-10, violations=[str(e)])
