import logging
import asyncio
from typing import Any

from core.worker_base import WorkerBase, WorkerResult
from core.reward import RewardStore
from services.guardian_service import guardian_instance
from services.notification_service import send_whatsapp_notification
import sounddevice as sd
import numpy as np
import time
import threading

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
        self.last_audio_peak = time.time()
        self._start_audio_monitor()

    def _start_audio_monitor(self):
        """Inicia uma thread separada para monitorar o RMS do áudio de saída."""
        def callback(indata, frames, time_info, status):
            volume_norm = np.linalg.norm(indata) * 10
            if volume_norm > self.silence_threshold:
                self.last_audio_peak = time.time()

        def monitor_thread():
            try:
                with sd.InputStream(callback=callback):
                    while True:
                        time.sleep(1)
            except Exception as e:
                logger.error(f"Erro no monitor de áudio: {e}")

        t = threading.Thread(target=monitor_thread, daemon=True)
        t.start()

    def run_cycle(self, **kwargs) -> WorkerResult:
        violations = []
        metadata = {}
        score = 0

        try:
            # 1. Executa o ciclo principal do GuardianService
            guardian_instance.run_cycle()
            
            # 2. Coleta status para o resultado
            process_status = guardian_instance.check_processes()
            health_metrics = guardian_instance.check_system_health()
            
            metadata["processes"] = process_status
            metadata["health"] = health_metrics
            
            # Helper para enviar notificações assíncronas
            def notify(msg):
                try:
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(send_whatsapp_notification(msg))
                    loop.close()
                except Exception as ne:
                    logger.error(f"Erro ao enviar notificação: {ne}")

            # 3. Verificação de Silêncio
            silence_duration = time.time() - self.last_audio_peak
            metadata["silence_seconds"] = round(silence_duration, 1)
            
            if silence_duration > self.silence_limit_seconds:
                msg = f"🔇 ALERTA: Silêncio detectado por {int(silence_duration)}s! Tentando retomar Play."
                violations.append(msg)
                score -= 15
                notify(msg)
                guardian_instance.trigger_play_on_zara()
                # Reset temporário para não floodar
                self.last_audio_peak = time.time() + 60 

            # 4. Avaliação básica de processos
            zara_running = process_status.get("zararadio") == "Running"
            if zara_running:
                score += 5
            else:
                msg = "🚨 ALERTA: ZaraRadio não está rodando!"
                violations.append(msg)
                score -= 10
                notify(msg)
                
            # Verifica BUTT (devem ser 3 instâncias)
            # Acessamos psutil através do guardian_instance que já o importa
            import psutil
            butt_count = sum(1 for p in psutil.process_iter(['name']) if p.info['name'].lower() == 'butt.exe')
            if butt_count < 3:
                msg = f"⚠️ ALERTA: Apenas {butt_count}/3 instâncias do BUTT rodando!"
                violations.append(msg)
                score -= 5
                notify(msg)

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
