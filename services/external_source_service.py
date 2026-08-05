"""
Serviço de Fonte Externa de Transmissão (ex.: NDI / Tribunal Pleno).

Quando uma transmissão especial ocorre (ex.: todas as quartas-feiras, o
Tribunal Pleno via NDI), o BUTT passa a transmitir áudio de uma fonte EXTERNA
ao ZaraRadio (que fica pausado/fora do ar).

Nesse modo, o sistema NÃO deve:
  - tentar reiniciar ou forçar play no ZaraRadio (isso quebraria o NDI no ar);
  - reportar o ZaraRadio como "parado/quebrado" (é o estado ESPERADO).

O modo pode ser ativado:
  (A) Manualmente (botão no cockpit: Iniciar/Encerrar);
  (B) Automaticamente por agenda (configurável em settings.json:
       special_transmission.day_of_week + start_hour/end_hour).

Estado mantido em memória (singleton). Não altera áudio nem volume.
"""

import threading
import logging
from datetime import datetime
from typing import Optional

from core.time_utils import now_local
from core.config_loader import get_settings

logger = logging.getLogger("OmniCore.ExternalSource")


class ExternalSourceService:
    def __init__(self):
        self._lock = threading.RLock()  # RLock: reentrante (start/stop chamam to_dict sob o lock)
        self.active = False
        self.source = None          # ex.: "NDI"
        self.program = None         # ex.: "Tribunal Pleno"
        self.started_at: Optional[str] = None
        self.manual = False         # True se ativado manualmente (override da agenda)
        self._auto_evaluated_today = None  # controle de log de avaliação automática

    # ── Configuração da agenda (settings.json) ──
    def _schedule_config(self) -> dict:
        try:
            s = get_settings()
            cfg = s.get("special_transmission", {})
        except Exception:
            cfg = {}
        return {
            "enabled": bool(cfg.get("enabled", True)),
            "day_of_week": int(cfg.get("day_of_week", 2)),   # 0=seg .. 6=dom; 2=quarta
            "start_hour": int(cfg.get("start_hour", 14)),
            "end_hour": int(cfg.get("end_hour", 18)),
            "source": str(cfg.get("source", "NDI")),
            "program": str(cfg.get("program", "Tribunal Pleno")),
        }

    # ── API pública ──
    def start(self, source: str = "NDI", program: str = "Tribunal Pleno", manual: bool = True) -> dict:
        with self._lock:
            self.active = True
            self.source = source
            self.program = program
            self.started_at = now_local().strftime("%Y-%m-%d %H:%M:%S")
            self.manual = manual
            logger.warning(f"[FONTE-EXTERNA] Transmissão EXTERNA INICIADA ({source} / {program}). "
                           f"Autocura do ZaraRadio SUSPENSA.")
            return self.to_dict()

    def stop(self, manual: bool = True) -> dict:
        with self._lock:
            was = self.active
            self.active = False
            self.source = None
            self.program = None
            self.started_at = None
            self.manual = False
            if was:
                logger.warning("[FONTE-EXTERNA] Transmissão EXTERNA ENCERRADA. Autocura do ZaraRadio restaurada.")
            return self.to_dict()

    def is_active(self) -> bool:
        with self._lock:
            return self.active

    def to_dict(self) -> dict:
        with self._lock:
            return {
                "active": self.active,
                "source": self.source,
                "program": self.program,
                "started_at": self.started_at,
                "manual": self.manual,
            }

    # ── Avaliação automática por agenda (chamada a cada ciclo do monitor) ──
    def evaluate_schedule(self) -> None:
        cfg = self._schedule_config()
        if not cfg["enabled"]:
            return
        now = now_local()
        in_window = (
            now.weekday() == cfg["day_of_week"]
            and cfg["start_hour"] <= now.hour < cfg["end_hour"]
        )
        with self._lock:
            # Se foi ativado manualmente, a agenda não desativa (override).
            if self.active and self.manual:
                return
            if in_window and not self.active:
                # Ativa automaticamente
                self.start(source=cfg["source"], program=cfg["program"], manual=False)
                logger.info(f"[FONTE-EXTERNA] Agenda automática ativou transmissão externa "
                            f"({cfg['source']} / {cfg['program']}).")
            elif not in_window and self.active and not self.manual:
                # Encerra automaticamente ao sair da janela
                self.stop(manual=False)
                logger.info("[FONTE-EXTERNA] Agenda automática encerrou transmissão externa (fora da janela).")


# Singleton
external_source_service = ExternalSourceService()
