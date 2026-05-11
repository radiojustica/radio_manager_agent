import logging
import json
from pathlib import Path
from typing import Any
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from core import state
from core.reward import RewardStore
from services.guardian_service import guardian_instance
from workers.playlist_worker import PlaylistWorker
from workers.audit_worker import AuditWorker
from workers.curadoria_worker import CuradoriaWorker
from workers.guardian_worker import GuardianWorker
from workers.sync_worker import SyncWorker
from workers.weather_worker import WeatherWorker
from workers.downloader_worker import DownloaderWorker
from workers.butt_worker import ButtWorker
from workers.update_worker import UpdateWorker

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
            "UpdateWorker": {"interval_hours": 1}  # Verifica atualizações a cada 1 hora
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
            return {
                "worker": name,
                "result": result.to_dict(),
                "health": worker.health(),
            }
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

        self.scheduler.start()
        logger.info("Orquestrador iniciado com sucesso dinamicamente.")

    def stop_orchestrator(self):
        """Para o agendamento de workers."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Orquestrador encerrado.")


def create_default_manager() -> WorkerManager:
    manager = WorkerManager()
    manager.register_worker(PlaylistWorker(reward_store=manager.reward_store))
    manager.register_worker(AuditWorker(reward_store=manager.reward_store))
    manager.register_worker(CuradoriaWorker(reward_store=manager.reward_store))
    manager.register_worker(GuardianWorker(reward_store=manager.reward_store))
    manager.register_worker(SyncWorker(reward_store=manager.reward_store))
    manager.register_worker(WeatherWorker(reward_store=manager.reward_store))
    manager.register_worker(DownloaderWorker(reward_store=manager.reward_store))
    manager.register_worker(ButtWorker(reward_store=manager.reward_store))
    manager.register_worker(UpdateWorker(reward_store=manager.reward_store))
    return manager

# Instância global para uso em todo o backend
worker_manager_instance = create_default_manager()
