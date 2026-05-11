import logging
from typing import Any
from core.worker_base import WorkerBase, WorkerResult
from core.reward import RewardStore
from services.notification_service import send_whatsapp_alert

logger = logging.getLogger("OmniCore.Workers.DailyReport")

class DailyReportWorker(WorkerBase):
    """
    Worker que compila e envia um relatório gerencial diário das atividades do Omni Core V2.
    """
    def __init__(self, reward_store: RewardStore | None = None, config: dict[str, Any] | None = None):
        super().__init__(name="DailyReportWorker", reward_store=reward_store, config=config)

    def run_cycle(self, **kwargs) -> WorkerResult:
        try:
            summary = self.reward_store.summary()
            
            # Cálculo de métricas básicas
            total_score = 0
            total_actions = 0
            guardian_fixes = 0
            
            report_lines = ["📊 *RELATÓRIO GERENCIAL - OMNI CORE V2*"]
            
            for worker_name, stats in summary.items():
                score = stats.get("score_total", 0)
                violations_count = len(stats.get("last_violations", []))
                
                total_score += score
                total_actions += stats.get("runs", 0)
                
                if worker_name == "GuardianWorker":
                    # Heurística: cada violação no Guardian costuma ser uma correção
                    guardian_fixes = violations_count
                
                report_lines.append(f"• *{worker_name}*: {score} pts ({stats.get('runs', 0)} ciclos)")

            report_lines.append(f"\n📈 *Resumo Executivo*:")
            report_lines.append(f"• Ações Processadas: {total_actions}")
            report_lines.append(f"• Correções do Guardião: {guardian_fixes}")
            report_lines.append(f"• Eficiência Global: {'Alta' if total_score > 0 else 'Crítica'}")
            report_lines.append(f"\n_Omni Core V2 AI Intelligence_")

            full_report = "\n".join(report_lines)
            
            # Envia o alerta
            send_whatsapp_alert(full_report)
            
            return WorkerResult(
                status="success", 
                score=10, 
                metadata={"report": full_report, "actions": total_actions}
            )

        except Exception as e:
            logger.error(f"Erro ao gerar relatório diário: {e}")
            return WorkerResult(status="error", score=-5, violations=[str(e)])
