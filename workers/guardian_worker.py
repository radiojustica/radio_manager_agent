import logging
import asyncio
from typing import Any

from core.worker_base import WorkerBase, WorkerResult
from core.reward import RewardStore
from services.guardian_service import guardian_instance
from services.notification_service import send_whatsapp_alert
from scripts.audio_manager import AudioManager

logger = logging.getLogger("OmniCore.Workers.Guardian")

class GuardianWorker(WorkerBase):
    """
    Worker responsável pela saúde do sistema de rádio (Watchdog).
    Monitora processos, reinicia se necessário, garante a reprodução e detecta silêncio.
    """
    def __init__(self, reward_store: RewardStore | None = None, config: dict[str, Any] | None = None):
        super().__init__(name="GuardianWorker", reward_store=reward_store, config=config)
        self.silence_threshold = self.config.get("silence_threshold", 0.005)
        self.silence_limit_seconds = self.config.get("silence_limit", 10)
        self.audio_manager = AudioManager()
        # Importando aqui para evitar dependência circular se houver
        import time
        self.last_audio_peak = time.time()
        self._start_audio_monitor()

    def _start_audio_monitor(self):
        """Inicia uma thread separada para monitorar o pico do áudio via WASAPI (AudioManager)."""
        import threading
        import time

        def monitor_thread():
            logger.info("Monitor de áudio via AudioManager iniciado (GuardianWorker).")
            while True:
                try:
                    # Tenta capturar o pico do dispositivo "RADIO" ou do padrão
                    peak = self.audio_manager.get_master_peak("RADIO")
                    if peak > self.silence_threshold:
                        self.last_audio_peak = time.time()
                except Exception as e:
                    logger.debug(f"Erro no monitor de áudio: {e}")
                time.sleep(1) # Checagem a cada 1 segundo é suficiente para silêncio

        t = threading.Thread(target=monitor_thread, daemon=True)
        t.start()

    def run_cycle(self, **kwargs) -> WorkerResult:
        violations = []
        metadata = {}
        score = 0
        import time

        try:
            # 1. Executa o ciclo principal do GuardianService
            guardian_instance.run_cycle()
            
            # 2. Coleta status para o resultado
            process_status = guardian_instance.check_processes()
            health_metrics = guardian_instance.check_system_health()
            
            metadata["processes"] = process_status
            metadata["health"] = health_metrics
            
            # 3. Verificação de Silêncio
            silence_duration = time.time() - self.last_audio_peak
            metadata["silence_seconds"] = round(silence_duration, 1)
            
            if silence_duration > self.silence_limit_seconds:
                msg = f"🔇 ALERTA: Silêncio detectado por {int(silence_duration)}s! Tentando retomar Play."
                violations.append(msg)
                score -= 15
                send_whatsapp_alert(msg)
                guardian_instance.trigger_play_on_zara()
                self.last_audio_peak = time.time() + 60 

            # 4. Detecção de Falha de Processo (ZaraRadio ou BUTT)
            zara_running = process_status.get("zararadio") == "Running"
            if not zara_running:
                msg = "🚨 ALERTA CRÍTICO: O processo ZaraRadio caiu e está sendo reiniciado pelo Guardian."
                violations.append(msg)
                score -= 10
                send_whatsapp_alert(msg)
                
            import psutil
            butt_count = sum(1 for p in psutil.process_iter(['name']) if p.info['name'].lower() == 'butt.exe')
            if butt_count < 3:
                msg = f"🚨 ALERTA CRÍTICO: O processo BUTT caiu (Apenas {butt_count}/3 rodando) e está sendo reiniciado pelo Guardian."
                violations.append(msg)
                score -= 5
                send_whatsapp_alert(msg)

            # Resto da lógica de avaliação
            if zara_running: score += 5
            
            recent_events = [e for e in guardian_instance.events_list if e['type'] in ('ERROR', 'WARNING', 'RESTART')][:5]
            if recent_events:
                metadata["recent_alerts"] = recent_events
            
            status = "success" if not violations else "partial_success"
            if not zara_running: status = "failed"
            
            return WorkerResult(status=status, score=score, violations=violations, metadata=metadata)

        except Exception as e:
            logger.error(f"Falha crítica no GuardianWorker: {e}")
            return WorkerResult(status="error", score=-20, violations=[str(e)], metadata={"error": str(e)})

    def high_frequency_checks(self):
        try:
            guardian_instance.check_vmix_and_switch()
            guardian_instance.check_ndi_session()
            guardian_instance.check_zara_track_and_trigger_vmix()
        except Exception as e:
            logger.debug(f"Erro em high_frequency_checks: {e}")
