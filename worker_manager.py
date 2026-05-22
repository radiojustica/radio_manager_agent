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
    logger.info("Importando ReportWorker...")
    from workers.report_worker import ReportWorker
    logger.info("Importando ApiWorker...")
    from workers.api_worker import ApiWorker
    logger.info("Importando NotificationWorker...")
    from workers.notification_worker import NotificationWorker
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
            "ApiWorker": {"interval_seconds": 30}
        }
        
        config_path = Path(__file__).resolve().parent / "config" / "settings.json"
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                merged = {**defaults, **data.get("workers", {})}
                if "ButtReconnect" in data.get("workers", {}) and "ButtWorker" not in merged:
                    merged["ButtWorker"] = data["workers"]["ButtReconnect"]
                return merged
            except Exception as e:
                logger.error(f"Erro ao carregar settings.json: {e}")
        
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
            self.run_cycle("PlaylistWorker", hora_inicio=0, mood=state.CURRENT_MOOD)

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

        # 9. DailyReportWorker (Relatório Gerencial às 18:00)
        self.scheduler.add_job(
            lambda: self.run_cycle("DailyReportWorker"),
            trigger=CronTrigger(hour=18, minute=0),
            id='worker_daily_report',
            replace_existing=True,
            misfire_grace_time=3600
        )

        # 10. BulletinWorker (Sincronização de Boletins)
        bulletin_cfg = self.config.get("BulletinWorker", {})
        self.scheduler.add_job(
            lambda: self.run_cycle("BulletinWorker"),
            trigger=IntervalTrigger(minutes=bulletin_cfg.get("interval_minutes", 30)),
            id='worker_bulletin',
            replace_existing=True
        )

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
    logger.info("Registrando BulletinWorker...")
    manager.register_worker(BulletinWorker(reward_store=manager.reward_store))
    logger.info("Registrando ReportWorker...")
    manager.register_worker(ReportWorker(reward_store=manager.reward_store))
    logger.info("Registrando ApiWorker...")
    manager.register_worker(ApiWorker(reward_store=manager.reward_store))
    logger.info("Registrando NotificationWorker...")
    manager.register_worker(NotificationWorker(reward_store=manager.reward_store))
    logger.info("Todos os workers registrados.")
    return manager

logger.info("Inicializando worker_manager_instance...")
worker_manager_instance = create_default_manager()
