import logging
from datetime import datetime
from sqlalchemy.orm import Session
from core.models import SystemConfig, AutopilotLog

logger = logging.getLogger("OmniCore.AutopilotService")

class AutopilotService:
    @staticmethod
    def is_autopilot_active(db: Session) -> bool:
        """Verifica se o piloto automático está ativado no banco de dados."""
        cfg = db.query(SystemConfig).filter(SystemConfig.key == "autopilot_active").first()
        if not cfg:
            # Por padrão, ativo
            cfg = SystemConfig(key="autopilot_active", value="true")
            db.add(cfg)
            db.commit()
            return True
        return cfg.value == "true"

    @staticmethod
    def set_autopilot_active(db: Session, active: bool) -> None:
        """Ativa ou desativa o piloto automático."""
        cfg = db.query(SystemConfig).filter(SystemConfig.key == "autopilot_active").first()
        val_str = "true" if active else "false"
        if not cfg:
            cfg = SystemConfig(key="autopilot_active", value=val_str)
            db.add(cfg)
        else:
            cfg.value = val_str
        db.commit()
        logger.info(f"Autopilot alterado para: {val_str.upper()}")

    @staticmethod
    def log_action(db: Session, action_type: str, message: str, success: bool = True) -> AutopilotLog:
        """Registra uma ação de autocura tomada pelo piloto automático."""
        from datetime import UTC
        log_entry = AutopilotLog(
            timestamp=datetime.now(UTC).replace(tzinfo=None),
            action_type=action_type,
            message=message,
            success=success
        )
        db.add(log_entry)
        db.commit()
        logger.info(f"[AUTOPILOT ACTION] {action_type} - {message} (Success: {success})")
        return log_entry

    @staticmethod
    def get_logs(db: Session, limit: int = 50) -> list[AutopilotLog]:
        """Obtém o histórico de ações de autocura."""
        return db.query(AutopilotLog).order_by(AutopilotLog.timestamp.desc()).limit(limit).all()

autopilot_service = AutopilotService()
