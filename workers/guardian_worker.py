import logging
from typing import Any

from core.worker_base import WorkerBase, WorkerResult
from core.reward import RewardStore
from services.guardian_service import guardian_instance

logger = logging.getLogger("OmniCore.Workers.Guardian")

class GuardianWorker(WorkerBase):
    """
    Worker responsável pela saúde do sistema de rádio (Watchdog).
    Monitora processos, reinicia se necessário e garante a reprodução.
    """
    def __init__(self, reward_store: RewardStore | None = None, config: dict[str, Any] | None = None):
        super().__init__(name="GuardianWorker", reward_store=reward_store, config=config)

    def run_cycle(self, **kwargs) -> WorkerResult:
        violations = []
        metadata = {}
        score = 0

        try:
            # 1. Executa o ciclo principal do GuardianService
            # Isso verifica processos, atividade e saúde do sistema.
            guardian_instance.run_cycle()
            
            # 2. Coleta status para o resultado
            process_status = guardian_instance.check_processes()
            health_metrics = guardian_instance.check_system_health()
            
            metadata["processes"] = process_status
            metadata["health"] = health_metrics
            
            # Avaliação básica para score
            zara_running = process_status.get("zararadio") == "Running"
            if zara_running:
                score += 5
            else:
                violations.append("ZaraRadio não está rodando!")
                score -= 10
                
            # Verifica se houve algum evento de reinicialização ou erro recente
            recent_events = [e for e in guardian_instance.events_list if e['type'] in ('ERROR', 'WARNING', 'RESTART')][:5]
            if recent_events:
                metadata["recent_alerts"] = recent_events
                for e in recent_events:
                    if e['type'] == 'ERROR':
                        score -= 5
                        violations.append(f"Erro detectado: {e['message']}")
            
            status = "success" if not violations else "partial_success"
            if not zara_running: status = "failed"
            
            return WorkerResult(status=status, score=score, violations=violations, metadata=metadata)

        except Exception as e:
            logger.error(f"Falha crítica no GuardianWorker: {e}")
            return WorkerResult(status="error", score=-20, violations=[str(e)], metadata={"error": str(e)})

    def high_frequency_checks(self):
        """
        Executa as checagens de alta frequência (vMix, NDI, Track).
        Pode ser chamado separadamente pelo scheduler a cada 1-2 segundos.
        """
        try:
            guardian_instance.check_vmix_and_switch()
            guardian_instance.check_ndi_session()
            guardian_instance.check_zara_track_and_trigger_vmix()
        except Exception as e:
            logger.debug(f"Erro em high_frequency_checks: {e}")
