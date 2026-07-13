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
        """Inicia uma thread separada para monitorar o pico do áudio de forma robusta e livre de falsos-positivos."""
        import threading
        import time

        def monitor_thread():
            logger.info("Monitor de áudio inteligente (dispositivo + processo) iniciado no GuardianWorker.")
            while True:
                try:
                    # 1. Tenta capturar o pico do dispositivo "RADIO"
                    peak = self.audio_manager.get_master_peak("RADIO")
                    
                    # 2. Se der silêncio no master ou erro, tenta obter direto da sessão de áudio do processo ZaraRadio
                    if peak <= self.silence_threshold:
                        proc_peak = self.audio_manager.get_process_peak("ZaraRadio.exe")
                        if proc_peak > self.silence_threshold:
                            peak = proc_peak
                        elif proc_peak < 0 and peak >= 0:
                            # Se a leitura do processo falhou com erro, mas a do master peak deu zero,
                            # mantém a do master peak
                            pass
                        elif proc_peak < 0 and peak < 0:
                            # Se ambas as leituras falharam, define como erro para evitar falso-positivo
                            peak = -1.0
                            
                    # 3. Trata o valor de pico
                    if peak > self.silence_threshold:
                        # Som detectado com sucesso
                        self.last_audio_peak = time.time()
                    elif peak < 0:
                        # Falha crítica de COM / Driver de Áudio (ex: -1.0)
                        # Blindagem de segurança: assume que está tocando para não matar o ZaraRadio em loop
                        self.last_audio_peak = time.time()
                except Exception as e:
                    logger.debug(f"Erro na thread do monitor de áudio: {e}")
                time.sleep(1)

        t = threading.Thread(target=monitor_thread, daemon=True)
        t.start()

    def run_cycle(self, **kwargs) -> WorkerResult:
        from core.database import SessionLocal
        from services.autopilot_service import autopilot_service
        
        db = SessionLocal()
        violations = []
        metadata = {}
        score = 0
        import time

        try:
            # 1. Verifica se o Autopilot está ativado no banco
            autopilot_active = autopilot_service.is_autopilot_active(db)
            metadata["autopilot_active"] = autopilot_active

            # 2. Executa o ciclo principal do GuardianService (que já respeita o Autopilot internamente)
            guardian_instance.run_cycle()
            
            # 3. Coleta status para o resultado
            process_status = guardian_instance.check_processes()
            health_metrics = guardian_instance.check_system_health()
            
            metadata["processes"] = process_status
            metadata["health"] = health_metrics
            
            # 4. Verificação de Silêncio
            silence_duration = time.time() - self.last_audio_peak
            metadata["silence_seconds"] = round(silence_duration, 1)
            
            zara_running = process_status.get("zararadio") == "Running"
            
            if silence_duration > self.silence_limit_seconds:
                msg = f"🔇 ALERTA: Silêncio detectado por {int(silence_duration)}s!"
                violations.append(msg)
                score -= 15
                
                if autopilot_active:
                    # DESATIVADO EMERGENCIALMENTE DURANTE TRANSMISSÕES AO VIVO
                    # O watchdog estava reiniciando o Zara erroneamente por "silêncio" quando o áudio 
                    # estava apenas baixo (ducking) durante a transmissão do Pleno via NDI.
                    
                    # if silence_duration > (self.silence_limit_seconds + 20) and zara_running:
                    #     msg_action = f"🔇 Silêncio contínuo por {int(silence_duration)}s. Forçando reinicialização do ZaraRadio."
                    #     autopilot_service.log_action(db, "SILENCE_RECOVERY", msg_action)
                    #     send_whatsapp_alert(f"🚨 Autopilot: {msg_action}")
                    #     guardian_instance.restart_zara()
                    #     self.last_audio_peak = time.time() + 45 # Dá 45s para o player carregar
                    # else:
                    #     msg_action = f"🔇 Silêncio detectado por {int(silence_duration)}s. Retomando reprodução via comando PLAY (P)."
                    #     autopilot_service.log_action(db, "SILENCE_RECOVERY", msg_action)
                    #     send_whatsapp_alert(f"🚨 Autopilot: {msg_action}")
                    #     guardian_instance.trigger_play_on_zara()
                    #     self.last_audio_peak = time.time() + 20 # Checa novamente em 20s
                    logger.info(f"🚨 Autopilot ativo, mas a autocura por silêncio ({int(silence_duration)}s) foi DESATIVADA para proteger transmissões ao vivo.")
                else:
                    logger.info(f"Autopilot inativo. Ignorando autocura para silêncio de {int(silence_duration)}s.")

            # 5. Detecção de Falha de Processo (ZaraRadio ou BUTT)
            if not zara_running:
                msg = "🚨 ALERTA CRÍTICO: O processo ZaraRadio está parado."
                violations.append(msg)
                score -= 10
                if autopilot_active:
                    autopilot_service.log_action(db, "PROCESS_RESTART", "Autopilot detectou ZaraRadio parado. Inicializando...")
                    send_whatsapp_alert(msg + " Autopilot reiniciando player.", title="🚨 Alerta: Player ZaraRadio Parou")
                else:
                    logger.info("Autopilot inativo. Ignorando reinício automático do ZaraRadio.")
                
            import psutil
            butt_count = sum(1 for p in psutil.process_iter(['name']) if p.info['name'].lower() == 'butt.exe')
            if butt_count < 3:
                msg = f"🚨 ALERTA CRÍTICO: Instâncias do encoder BUTT insuficientes ({butt_count}/3 rodando)."
                violations.append(msg)
                score -= 5
                if autopilot_active:
                    autopilot_service.log_action(db, "BUTT_RECONNECT", f"BUTT com {butt_count}/3 instâncias ativas. Tentando estabilizar...")
                    send_whatsapp_alert(msg + " Autopilot tentando restabelecer conexões.", title="🚨 Alerta: Encoders BUTT Instáveis")
                else:
                    logger.info("Autopilot inativo. Ignorando estabilização automática do BUTT.")

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
        finally:
            db.close()

    def high_frequency_checks(self):
        try:
            guardian_instance.check_vmix_and_switch()
            guardian_instance.check_ndi_session()
            guardian_instance.check_zara_track_and_trigger_vmix()
        except Exception as e:
            logger.debug(f"Erro em high_frequency_checks: {e}")
