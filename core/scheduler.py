# core/scheduler.py
"""Scheduler de tarefas automáticas para o Omni Core V2.
Agenda a geração automática de blocos de programa a cada hora usando APScheduler.
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from director.playlist_engine import playlist_engine_instance

logger = logging.getLogger("OmniCore.Scheduler")

scheduler = BackgroundScheduler()

def start_scheduler() -> None:
    """Inicializa e inicia o scheduler.
    Agenda a geração automática de blocos a cada hora, no minuto 0.
    """
    scheduler.add_job(
        func=playlist_engine_instance.auto_gerar_proximos_blocos,
        trigger="cron",
        minute=0,
        id="auto_gerar_proximos_blocos",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("APScheduler iniciado: geração automática de blocos a cada hora.")

def shutdown_scheduler() -> None:
    """Encerra o scheduler ao finalizar a aplicação."""
    scheduler.shutdown()
    logger.info("APScheduler encerrado.")
