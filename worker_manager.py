import logging
import json
from pathlib import Path
from typing import Any
from datetime import datetime
from core.time_utils import now_local
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from core import state
from core.reward import RewardStore
from services.guardian_service import guardian_instance

logger = logging.getLogger("OmniCore.WorkerManager")

try:
    logger.info("Importando PlaylistWorker...")
    from workers.playlist_worker import PlaylistWorker
    logger.info("Importando AuditWorker...")
    from workers.audit_worker import AuditWorker
    logger.info("Importando CuradoriaWorker...")
    from workers.curadoria_worker import CuradoriaWorker
    logger.info("Importando GuardianWorker...")
    from workers.guardian_worker import GuardianWorker
    logger.info("Importando SyncWorker...")
    from workers.sync_worker import SyncWorker
    logger.info("Importando WeatherWorker...")
    from workers.weather_worker import WeatherWorker
    logger.info("Importando DownloaderWorker...")
    from workers.downloader_worker import DownloaderWorker
    logger.info("Importando ButtWorker...")
    from workers.butt_worker import ButtWorker
    logger.info("Importando UpdateWorker...")
    from workers.update_worker import UpdateWorker
    logger.info("Importando DailyReportWorker...")
    from workers.daily_report_worker import DailyReportWorker
    logger.info("Importando BulletinWorker...")
    from workers.bulletin_worker import BulletinWorker
    logger.info("Importando NjudWorker...")
    from workers.njud_worker import NjudWorker
    logger.info("Importando ReportWorker...")
    from workers.report_worker import ReportWorker
    logger.info("Importando ApiWorker...")
    from workers.api_worker import ApiWorker
    logger.info("Importando NotificationWorker...")
    from workers.notification_worker import NotificationWorker
    logger.info("Importando CommunicationWorker...")
    from workers.communication_worker import CommunicationWorker
    logger.info("Importando GiroWorker...")
    from workers.giro_worker import GiroWorker
    logger.info("Importando ContentGenerationWorker...")
    from workers.content_generation_worker import ContentGenerationWorker
    logger.info("Importando SpiderWorker...")
    from workers.spider_worker import SpiderWorker
except Exception as e:
    logger.error(f"ERRO FATAL DURANTE IMPORTAÇÃO DE WORKERS: {e}")
    import traceback
    logger.error(traceback.format_exc())
    raise e

logger = logging.getLogger("OmniCore.WorkerManager")

class WorkerManager:
    def __init__(self, reward_path: str | None = None):
        self.reward_store = RewardStore(reward_path)
        self.workers: dict[str, Any] = {}
        self.scheduler = BackgroundScheduler()
        self.config = self._load_config()

    def _load_config(self) -> dict[str, Any]:
        """Carrega configurações dos workers de settings.json com fallbacks."""
        defaults = {
            "GuardianWorker": {"interval_seconds": 30, "high_freq_seconds": 2},
            "CuradoriaWorker": {"interval_minutes": 5},
            "WeatherWorker": {"interval_minutes": 30},
            "SyncWorker": {"interval_hours": 4},
            "AuditWorker": {"interval_hours": 1},
            "PlaylistWorker": {"daily_hour": 0, "daily_minute": 0},
            "ButtWorker": {"interval_minutes": 2},
            "ButtReconnect": {"interval_minutes": 2},
            "UpdateWorker": {"interval_hours": 1},  # Verifica atualizações a cada 1 hora
            "BulletinWorker": {"interval_minutes": 30},
            "ApiWorker": {"interval_seconds": 30},
            "GiroWorker": {"sync_day_of_week": "sun", "sync_hour": 5, "sync_minute": 0},
            "ContentGenerationWorker": {"daily_hour": 6, "daily_minute": 0}
        }
        
        try:
            from core.config_loader import get_settings
            data = get_settings()
            if data:
                merged = {**defaults, **data.get("workers", {})}
                if "ButtReconnect" in data.get("workers", {}) and "ButtWorker" not in merged:
                    merged["ButtWorker"] = data["workers"]["ButtReconnect"]
                return merged
        except Exception as e:
            logger.error(f"Erro ao carregar configurações dos workers pelo config_loader: {e}")
        
        return defaults

    def register_worker(self, worker: Any) -> None:
        self.workers[worker.name] = worker

    def get_worker(self, name: str) -> Any | None:
        return self.workers.get(name)

    def run_cycle(self, name: str, **kwargs) -> dict[str, Any]:
        try:
            worker = self.get_worker(name)
            if not worker:
                raise ValueError(f"Worker desconhecido: {name}")
            result = worker.execute_cycle(**kwargs)
            
            response_data = {
                "worker": name,
                "result": result.to_dict(),
                "health": worker.health(),
            }

            # Registrar evento de worker no guardião para exibição no histórico
            try:
                status_text = result.status.upper() if getattr(result, "status", None) else "DESCONHECIDO"
                score_text = f" (Score: {result.score})" if hasattr(result, "score") else ""
                if getattr(result, "status", None) == "error":
                    msg = f"Falha no Worker [{name}]: {', '.join(result.violations) if result.violations else 'Erro desconhecido'}"
                    guardian_instance.log_event("WARNING", msg)
                elif getattr(result, "status", None) == "circuit_breaker_open":
                    msg = f"Worker [{name}] bloqueado (Circuit Breaker aberto)"
                    guardian_instance.log_event("WARNING", msg)
                else:
                    msg = f"Worker [{name}] executou com sucesso (Status: {status_text}){score_text}"
                    guardian_instance.log_event("WORKER", msg)
            except Exception as le:
                logger.error(f"Erro ao registrar log de evento do worker: {le}")

            # Notifica via WebSocket sobre a conclusão do ciclo
            try:
                from api.manager import broadcast_event
                import asyncio
                
                event_data = {
                    "type": "worker_cycle",
                    "worker": name,
                    "status": result.status if hasattr(result, "status") else "unknown",
                    "score": result.score if hasattr(result, "score") else 0,
                    "metadata": result.metadata if hasattr(result, "metadata") else {},
                    "timestamp": now_local().isoformat()
                }
                
                # Executa o broadcast de forma segura entre threads
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.run_coroutine_threadsafe(broadcast_event(event_data), loop)
                    else:
                        loop.run_until_complete(broadcast_event(event_data))
                except RuntimeError:
                    # Se não houver loop na thread atual, criamos um temporário
                    asyncio.run(broadcast_event(event_data))
            except Exception as broadcast_err:
                logger.debug(f"Aviso: Não foi possível enviar broadcast (API pode estar offline): {broadcast_err}")

            return response_data
        except Exception as e:
            logger.error(f"Erro crítico no orquestrador para o worker {name}: {e}")
            try:
                guardian_instance.log_event("WARNING", f"Erro crítico no Worker [{name}]: {str(e)}")
            except Exception:
                pass
            # Registro persistente de falha crítica no RewardStore
            try:
                self.reward_store.record(
                    worker_name=name or "UnknownManager",
                    score=-10,
                    violations=["CRITICAL_MANAGER_FAILURE"],
                    metadata={"error": str(e), "manager_failure": True}
                )
            except Exception as re:
                logger.error(f"Falha adicional ao registrar erro no RewardStore: {re}")

            return {
                "worker": name,
                "result": {"status": "error", "violations": [f"CRITICAL: {str(e)}"]},
                "health": {"running": False, "error": str(e)}
            }

    def run_all(self) -> dict[str, Any]:
        results: dict[str, Any] = {}
        for name, worker in self.workers.items():
            results[name] = self.run_cycle(name)
        return results

    def start_orchestrator(self):
        """Inicializa o agendamento contínuo de todos os workers."""
        if self.scheduler.running:
            logger.warning("Orquestrador já está em execução.")
            return

        logger.info("Iniciando Orquestrador de Workers (Fase 3)...")

        # Desabilita as tarefas de reboot/manutenção indesejadas imediatamente no startup
        try:
            logger.info("[Startup] Desativando tarefas de reboot indesejadas via guardian_instance...")
            guardian_instance.disable_weekly_reboot_task()
        except Exception as e:
            logger.error(f"[Startup] Erro ao desativar tarefas de reboot no startup: {e}")

        # 1. GuardianWorker (Watchdog e Alta Frequência)
        guardian_cfg = self.config.get("GuardianWorker", {})
        self.scheduler.add_job(
            lambda: self.run_cycle("GuardianWorker"),
            trigger=IntervalTrigger(seconds=guardian_cfg.get("interval_seconds", 30)),
            id='worker_guardian_watchdog',
            replace_existing=True
        )

        guardian = self.get_worker("GuardianWorker")
        if guardian and hasattr(guardian, 'high_frequency_checks'):
            self.scheduler.add_job(
                guardian.high_frequency_checks,
                trigger=IntervalTrigger(seconds=guardian_cfg.get("high_freq_seconds", 2)),
                id='worker_guardian_high_freq',
                replace_existing=True
            )

        # 2. CuradoriaWorker
        curadoria_cfg = self.config.get("CuradoriaWorker", {})
        self.scheduler.add_job(
            lambda: self.run_cycle("CuradoriaWorker"),
            trigger=IntervalTrigger(minutes=curadoria_cfg.get("interval_minutes", 5)),
            id='worker_curadoria',
            replace_existing=True
        )

        # 3. WeatherWorker (com atualização de estado)
        weather_cfg = self.config.get("WeatherWorker", {})
        def weather_job():
            response = self.run_cycle("WeatherWorker")
            if response["result"]["status"] == "success":
                state.CURRENT_MOOD = response["result"]["metadata"].get("mood", "Ensolarado")

        self.scheduler.add_job(
            weather_job,
            trigger=IntervalTrigger(minutes=weather_cfg.get("interval_minutes", 30)),
            id='worker_weather',
            replace_existing=True
        )

        # 4. SyncWorker
        sync_cfg = self.config.get("SyncWorker", {})
        self.scheduler.add_job(
            lambda: self.run_cycle("SyncWorker"),
            trigger=IntervalTrigger(hours=sync_cfg.get("interval_hours", 4)),
            id='worker_sync',
            replace_existing=True
        )

        # 5. AuditWorker
        audit_cfg = self.config.get("AuditWorker", {})
        self.scheduler.add_job(
            lambda: self.run_cycle("AuditWorker"),
            trigger=IntervalTrigger(hours=audit_cfg.get("interval_hours", 1)),
            id='worker_audit',
            replace_existing=True
        )

        # 6. PlaylistWorker (Geração Diária)
        playlist_cfg = self.config.get("PlaylistWorker", {})
        def daily_playlist_job():
            self.run_cycle("PlaylistWorker", hora_inicio=None, mood=state.CURRENT_MOOD)

        self.scheduler.add_job(
            daily_playlist_job,
            trigger=CronTrigger(
                hour=playlist_cfg.get("daily_hour", 0), 
                minute=playlist_cfg.get("daily_minute", 0)
            ),
            id='worker_daily_playlist',
            replace_existing=True,
            misfire_grace_time=3600
        )

        # 7. Tarefas auxiliares de manutenção (Guardian)
        butt_cfg = self.config.get("ButtWorker", self.config.get("ButtReconnect", {}))
        self.scheduler.add_job(
            lambda: self.run_cycle("ButtWorker"),
            trigger=IntervalTrigger(minutes=butt_cfg.get("interval_minutes", 2)),
            id='worker_butt_reconnect',
            replace_existing=True
        )

        # 8. UpdateWorker (Verificação de atualizações)
        update_cfg = self.config.get("UpdateWorker", {})
        self.scheduler.add_job(
            lambda: self.run_cycle("UpdateWorker"),
            trigger=IntervalTrigger(hours=update_cfg.get("interval_hours", 1)),
            id='worker_update_checker',
            replace_existing=True
        )

        self.scheduler.add_job(
            guardian_instance.disable_weekly_reboot_task,
            trigger=CronTrigger(hour=21, minute=59),
            id='reboot_block_daily',
            replace_existing=True
        )

        # 9. DailyReportWorker (Relatório Gerencial às 18:00) - Comentado para evitar duplicidade com o CommunicationWorker
        # self.scheduler.add_job(
        #     lambda: self.run_cycle("DailyReportWorker"),
        #     trigger=CronTrigger(hour=18, minute=0),
        #     id='worker_daily_report',
        #     replace_existing=True,
        #     misfire_grace_time=3600
        # )

        # --- INÍCIO: DESATIVADO POR ORDEM DO USUÁRIO (SEM IA ATÉ SEGUNDA ORDEM) ---
        """
        # 10. BulletinWorker (Sincronização de Boletins 3x ao dia)
        for idx, (h, m) in enumerate([(11, 30), (15, 30), (20, 30)]):
            self.scheduler.add_job(
                lambda: self.run_cycle("BulletinWorker"),
                trigger=CronTrigger(hour=h, minute=m),
                id=f'worker_bulletin_cron_{idx}',
                replace_existing=True,
                misfire_grace_time=3600
            )

        # 10b. NjudWorker (Sincronização do Notícias do Judiciário 3x ao dia)
        for idx, (h, m) in enumerate([(11, 0), (15, 0), (20, 0)]):
            self.scheduler.add_job(
                lambda: self.run_cycle("NjudWorker"),
                trigger=CronTrigger(hour=h, minute=m),
                id=f'worker_njud_cron_{idx}',
                replace_existing=True,
                misfire_grace_time=3600
            )

        # 10c. GiroWorker (Sincronização do Giro das Comarcas - Semanal)
        giro_cfg = self.config.get("GiroWorker", {})
        self.scheduler.add_job(
            lambda: self.run_cycle("GiroWorker"),
            trigger=CronTrigger(
                day_of_week=giro_cfg.get("sync_day_of_week", "sun"),
                hour=giro_cfg.get("sync_hour", 5),
                minute=giro_cfg.get("sync_minute", 0)
            ),
            id='worker_giro_sync',
            replace_existing=True,
            misfire_grace_time=3600
        )

        # 10d. ContentGenerationWorker (Geração de IA - Diário)
        content_cfg = self.config.get("ContentGenerationWorker", {})
        self.scheduler.add_job(
            lambda: self.run_cycle("ContentGenerationWorker"),
            trigger=CronTrigger(
                hour=content_cfg.get("daily_hour", 6),
                minute=content_cfg.get("daily_minute", 0)
            ),
            id='worker_content_generation',
            replace_existing=True,
            misfire_grace_time=3600
        )
        """
        # --- FIM: DESATIVADO POR ORDEM DO USUÁRIO ---

        # 11. DownloaderWorker (Aquisição Proativa às 01:00)
        downloader_cfg = self.config.get("DownloaderWorker", {})
        self.scheduler.add_job(
            lambda: self.run_cycle("DownloaderWorker"),
            trigger=CronTrigger(
                hour=downloader_cfg.get("proactive_hour", 1), 
                minute=downloader_cfg.get("proactive_minute", 0)
            ),
            id='worker_proactive_downloader',
            replace_existing=True,
            misfire_grace_time=3600
        )

        # 12. ApiWorker (Servidor API e Health Check)
        api_cfg = self.config.get("ApiWorker", {})
        self.scheduler.add_job(
            lambda: self.run_cycle("ApiWorker"),
            trigger=IntervalTrigger(seconds=api_cfg.get("interval_seconds", 30)),
            id='worker_api_server',
            replace_existing=True
        )

        # 13. NotificationWorker (Heartbeat e Gestão de Alertas)
        notif_cfg = self.config.get("NotificationWorker", {})
        self.scheduler.add_job(
            lambda: self.run_cycle("NotificationWorker"),
            trigger=IntervalTrigger(minutes=notif_cfg.get("interval_minutes", 60)),
            id='worker_notification',
            replace_existing=True
        )

        # 13b. CommunicationWorker (Resumos Consolidados 2x ao dia: 08:00 e 20:00)
        self.scheduler.add_job(
            lambda: self.run_cycle("CommunicationWorker"),
            trigger=CronTrigger(hour="8,20", minute=0),
            id='worker_communication_summary',
            replace_existing=True,
            misfire_grace_time=3600
        )

        # 14. Playlist Maintenance (Garantir que blocos existam e estejam atualizados)
        try:
            from director.playlist_engine import playlist_engine_instance
            self.scheduler.add_job(
                lambda: playlist_engine_instance.auto_gerar_proximos_blocos(),
                trigger=IntervalTrigger(hours=1),
                id='worker_playlist_maintenance',
                replace_existing=True
            )
        except ImportError:
            logger.error("Não foi possível importar playlist_engine_instance para manutenção.")

        # Garante que a API inicie imediatamente no startup
        try:
            logger.info("Forçando inicialização imediata do ApiWorker...")
            self.run_cycle("ApiWorker")
        except Exception as e:
            logger.error(f"Erro ao forçar inicialização imediata do ApiWorker: {e}")

        self.scheduler.start()
        logger.info("Orquestrador iniciado com sucesso dinamicamente.")

        # Inicia o listener de comandos ntfy (mesmo canal radio_tjrn)
        try:
            from services.ntfy_listener_service import ntfy_listener_service
            ntfy_listener_service.start(self)
            logger.info("✓ NtfyListenerService iniciado no canal radio_tjrn.")
        except Exception as ntfy_err:
            logger.error(f"[NtfyListener] Falha ao iniciar o listener ntfy: {ntfy_err}")


        # Inscrição do Pub/Sub para validação assíncrona de playlists geradas
        try:
            from services.pubsub_service import pubsub_service_instance
            from core.compliance_validator import compliance_validator_instance
            
            def processar_bloco_gerado(msg: dict):
                logger.info(f"[Orquestrador/PubSub] Recebido evento de bloco gerado: {msg}")
                hora_inicio = msg.get("hora_inicio")
                caminho_m3u = msg.get("caminho_m3u")
                mood = msg.get("mood", "Desconhecido")
                
                if hora_inicio is not None and caminho_m3u:
                    # Executa validação regulatória rígida (Camada 1)
                    violations = compliance_validator_instance.validate_playlist(caminho_m3u, hora_inicio)
                    status = "success" if not violations else "failed"
                    
                    # Publica resultado no canal auditoria:resultado
                    try:
                        pubsub_service_instance.publish("auditoria:resultado", {
                            "hora_inicio": hora_inicio,
                            "caminho_m3u": caminho_m3u,
                            "mood": mood,
                            "status": status,
                            "violations": violations,
                            "timestamp": datetime.now().isoformat()
                        })
                        logger.info(f"[Orquestrador/PubSub] Resultado publicado em auditoria:resultado para bloco {hora_inicio:02d}H: {status}")
                    except Exception as pe:
                        logger.error(f"[Orquestrador/PubSub] Erro ao publicar resultado em auditoria:resultado: {pe}")
            
            pubsub_service_instance.subscribe("auditoria:bloco_gerado", processar_bloco_gerado)
            logger.info("✓ Orquestrador subscrito no canal auditoria:bloco_gerado com sucesso.")
        except Exception as e:
            logger.error(f"[Orquestrador/PubSub] Erro crítico ao se inscrever no canal de PubSub: {e}")

    def stop_orchestrator(self):
        """Para o agendamento de workers."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Orquestrador encerrado.")


def create_default_manager() -> WorkerManager:
    logger.info("Criando gerente de workers padrão...")
    manager = WorkerManager()
    logger.info("Registrando PlaylistWorker...")
    manager.register_worker(PlaylistWorker(reward_store=manager.reward_store))
    logger.info("Registrando AuditWorker...")
    manager.register_worker(AuditWorker(reward_store=manager.reward_store))
    logger.info("Registrando CuradoriaWorker...")
    manager.register_worker(CuradoriaWorker(reward_store=manager.reward_store))
    logger.info("Registrando GuardianWorker...")
    manager.register_worker(GuardianWorker(reward_store=manager.reward_store))
    logger.info("Registrando SyncWorker...")
    manager.register_worker(SyncWorker(reward_store=manager.reward_store))
    logger.info("Registrando WeatherWorker...")
    manager.register_worker(WeatherWorker(reward_store=manager.reward_store))
    logger.info("Registrando DownloaderWorker...")
    manager.register_worker(DownloaderWorker(reward_store=manager.reward_store))
    logger.info("Registrando ButtWorker...")
    manager.register_worker(ButtWorker(reward_store=manager.reward_store))
    logger.info("Registrando UpdateWorker...")
    manager.register_worker(UpdateWorker(reward_store=manager.reward_store))
    logger.info("Registrando DailyReportWorker...")
    manager.register_worker(DailyReportWorker(reward_store=manager.reward_store))
    enable_ai = manager.config.get("enable_ai_workers", False)
    if enable_ai:
        logger.info("Registrando BulletinWorker...")
        manager.register_worker(BulletinWorker(reward_store=manager.reward_store))
        logger.info("Registrando NjudWorker...")
        manager.register_worker(NjudWorker(reward_store=manager.reward_store))
    else:
        logger.info("BulletinWorker e NjudWorker desativados (IA suspensa).")
        
    logger.info("Registrando ReportWorker...")
    manager.register_worker(ReportWorker(reward_store=manager.reward_store))
    logger.info("Registrando ApiWorker...")
    manager.register_worker(ApiWorker(reward_store=manager.reward_store))
    logger.info("Registrando NotificationWorker...")
    manager.register_worker(NotificationWorker(reward_store=manager.reward_store))
    logger.info("Registrando CommunicationWorker...")
    manager.register_worker(CommunicationWorker(reward_store=manager.reward_store))
    
    if enable_ai:
        logger.info("Registrando GiroWorker...")
        manager.register_worker(GiroWorker(reward_store=manager.reward_store))
        logger.info("Registrando ContentGenerationWorker...")
        manager.register_worker(ContentGenerationWorker(reward_store=manager.reward_store))
    else:
        logger.info("GiroWorker e ContentGenerationWorker desativados (IA suspensa).")
        
    logger.info("Registrando SpiderWorker...")
    manager.register_worker(SpiderWorker(reward_store=manager.reward_store))
    logger.info("Todos os workers registrados.")
    return manager

logger.info("Inicializando worker_manager_instance...")
worker_manager_instance = create_default_manager()
