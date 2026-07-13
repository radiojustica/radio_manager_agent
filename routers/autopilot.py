from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from core.models import AutopilotLog
from services.autopilot_service import autopilot_service
from pydantic import BaseModel

router = APIRouter(prefix="/api/autopilot", tags=["Autopilot"])

class AutopilotToggleSchema(BaseModel):
    active: bool

@router.get("/status")
def get_autopilot_status(db: Session = Depends(get_db)):
    """Retorna o status atual do Autopilot, estatísticas agregadas e logs recentes."""
    try:
        active = autopilot_service.is_autopilot_active(db)
        
        # Agrega estatísticas de autocura
        restarts = db.query(AutopilotLog).filter(AutopilotLog.action_type == "PROCESS_RESTART", AutopilotLog.success == True).count()
        silence_recoveries = db.query(AutopilotLog).filter(AutopilotLog.action_type == "SILENCE_RECOVERY", AutopilotLog.success == True).count()
        butt_reconnects = db.query(AutopilotLog).filter(AutopilotLog.action_type == "BUTT_RECONNECT", AutopilotLog.success == True).count()
        
        # Histórico recente (últimas 20 ações)
        recent_logs = db.query(AutopilotLog).order_by(AutopilotLog.timestamp.desc()).limit(20).all()
        
        logs_formatted = []
        for l in recent_logs:
            logs_formatted.append({
                "id": l.id,
                # Sufixo 'Z' informa ao browser que é UTC → toLocaleTimeString converte p/ horário local
                "timestamp": (l.timestamp.isoformat() + "Z") if l.timestamp else None,
                "action_type": l.action_type,
                "message": l.message,
                "success": l.success
            })
            
        return {
            "active": active,
            "stats": {
                "process_restarts": restarts,
                "silence_recoveries": silence_recoveries,
                "butt_reconnects": butt_reconnects
            },
            "recent_actions": logs_formatted
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter status do Autopilot: {str(e)}")

@router.post("/toggle")
def toggle_autopilot(payload: AutopilotToggleSchema, db: Session = Depends(get_db)):
    """Liga ou desliga o piloto automático do sistema."""
    try:
        autopilot_service.set_autopilot_active(db, payload.active)
        state_str = "ATIVADO" if payload.active else "DESATIVADO"
        autopilot_service.log_action(db, "SYSTEM_CONTROL", f"Piloto automático {state_str} manualmente pelo painel do usuário.")
        return {"success": True, "active": payload.active}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao alterar estado do Autopilot: {str(e)}")
