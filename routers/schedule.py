from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from core.models import SystemConfig
import json
import logging
from director.grade_rules import recarregar_config

router = APIRouter(prefix="/api/schedule", tags=["Grade Semanal"])
logger = logging.getLogger("OmniCore.RouterSchedule")

GRADE_PADRAO = {
    "legendas": {
        "SPOT": {"tipo": "vinheta", "duracao": "curto", "pasta": "D:\\RADIO\\SPOTS"},
        "VH_INSTITUCIONAL": {"tipo": "vinheta", "duracao": "curto", "pasta": "D:\\RADIO\\VINHETAS"},
        "BOLETIM": {"tipo": "boletim", "duracao": "1-2 min", "pasta_raiz": "D:\\SERVIDOR\\BOLETINS"},
        "PROGRAMAS": {
            "GIRO_NAS_COMARCAS": {"duracao_minutos": 10, "pasta": "D:\\SERVIDOR\\PROGRAMAS\\PROGRAMA_40\\GIRONASCOMARCAS"},
            "MEMORIA_DA_JUSTICA": {"duracao_minutos": 40, "pasta": "D:\\SERVIDOR\\PROGRAMAS\\PROGRAMA_40\\MEMORIA"},
            "LEVEMENTE": {"duracao_minutos": 40, "pasta": "D:\\SERVIDOR\\PROGRAMAS\\PROGRAMA_40\\LEVEMENTE"},
            "NOTICIAS_DO_JUDICIARIO": {"duracao_minutos": 5, "pasta": "D:\\SERVIDOR\\DRIVE\\RADIO TJRN CONTEÚDO\\NOT JUDICIARIO (5 MIN)"}
        }
    },
    "grade_diaria": {
        "madrugada_manha": {
            "inicio": "00:01",
            "fim": "08:30",
            "loop": {"intervalo_minutos": 30, "estrutura": ["SPOT", "BOLETIM", "SPOT"]}
        },
        "noite_madrugada": {
            "inicio": "18:00",
            "fim": "23:59",
            "loop": {"intervalo_minutos": 30, "estrutura": ["SPOT", "BOLETIM", "SPOT"]}
        }
    },
    "excecoes_diurnas": {
        "segunda": {
            "09:00": ["SPOT", "BOLETIM", "SPOT", "MUSICA"],
            "10:00": ["SPOT", "BOLETIM", "SPOT", "MUSICA"],
            "10:45": ["SPOT", "NOTICIAS_DO_JUDICIARIO", "SPOT", "MUSICA"],
            "11:30": ["SPOT", "VH_INSTITUCIONAL", "SPOT", "MUSICA"],
            "12:00": ["SPOT", "BOLETIM", "SPOT", "MUSICA"],
            "16:00": ["VH_INSTITUCIONAL", "MEMORIA_DA_JUSTICA", "MUSICA"],
            "17:30": ["NOTICIAS_DO_JUDICIARIO"]
        },
        "terca": {
            "09:00": ["SPOT", "VH_INSTITUCIONAL", "MUSICA"],
            "10:00": ["SPOT", "VH_INSTITUCIONAL", "MUSICA"],
            "10:45": ["SPOT", "NOTICIAS_DO_JUDICIARIO", "SPOT", "MUSICA"],
            "11:30": ["SPOT", "BOLETIM", "SPOT", "MUSICA"],
            "12:00": ["SPOT", "BOLETIM", "SPOT", "MUSICA"],
            "15:00": ["SPOT", "BOLETIM", "GIRO_NAS_COMARCAS", "MUSICA"],
            "17:30": ["NOTICIAS_DO_JUDICIARIO"]
        },
        "quarta": {
            "09:00": ["SPOT", "BOLETIM", "SPOT", "MUSICA"],
            "10:00": ["SPOT", "BOLETIM", "SPOT", "MUSICA"],
            "10:45": ["SPOT", "NOTICIAS_DO_JUDICIARIO", "SPOT", "MUSICA"],
            "11:30": ["SPOT", "BOLETIM", "SPOT", "MUSICA"],
            "12:00": ["SPOT", "BOLETIM", "SPOT", "MUSICA"],
            "17:30": ["NOTICIAS_DO_JUDICIARIO"]
        },
        "quinta": {
            "09:00": ["SPOT", "VH_INSTITUCIONAL", "LEVEMENTE", "MUSICA"],
            "10:00": ["SPOT", "BOLETIM", "SPOT", "MUSICA"],
            "10:45": ["SPOT", "NOTICIAS_DO_JUDICIARIO", "SPOT", "MUSICA"],
            "11:30": ["SPOT", "BOLETIM", "SPOT", "MUSICA"],
            "12:00": ["SPOT", "BOLETIM", "SPOT", "MUSICA"],
            "17:30": ["NOTICIAS_DO_JUDICIARIO"]
        },
        "sexta": {
            "09:00": ["SPOT", "VH_INSTITUCIONAL", "MUSICA"],
            "10:00": ["SPOT", "BOLETIM", "SPOT", "MUSICA"],
            "10:45": ["SPOT", "NOTICIAS_DO_JUDICIARIO", "SPOT", "MUSICA"],
            "11:30": ["SPOT", "VH_INSTITUCIONAL", "SPOT", "MUSICA"],
            "12:00": ["SPOT", "VH_INSTITUCIONAL", "MUSICA"],
            "17:30": ["NOTICIAS_DO_JUDICIARIO"]
        }
    },
    "final_de_semana": {
        "sabado": {
            "06:00_15:00": {"loop": {"intervalo_minutos": 30, "estrutura": ["SPOT", "BOLETIM", "SPOT", "MUSICA"]}},
            "15:00_18:00": {"loop": {"intervalo_minutos": 30, "estrutura": ["SPOT", "BOLETIM", "SPOT", "MUSICA"]}}
        },
        "domingo": {
            "06:00_15:00": {"loop": {"intervalo_minutos": 30, "estrutura": ["SPOT", "BOLETIM", "SPOT", "MUSICA"]}},
            "15:00_18:00": {"loop": {"intervalo_minutos": 30, "estrutura": ["SPOT", "BOLETIM", "SPOT", "MUSICA"]}}
        }
    }
}

@router.get("/weekly")
async def get_weekly_schedule(db: Session = Depends(get_db)):
    """Retorna a grade horária semanal salva no SQLite."""
    config = db.query(SystemConfig).filter(SystemConfig.key == "weekly_schedule").first()
    if not config:
        # Se não existir, retorna a de fábrica
        return GRADE_PADRAO
    try:
        return json.loads(config.value)
    except Exception as e:
        logger.error(f"Erro ao decodificar weekly_schedule do banco: {e}")
        return GRADE_PADRAO

@router.post("/weekly")
async def save_weekly_schedule(grade_data: dict, db: Session = Depends(get_db)):
    """Salva a grade horária semanal no SQLite."""
    try:
        config = db.query(SystemConfig).filter(SystemConfig.key == "weekly_schedule").first()
        value_str = json.dumps(grade_data, indent=4)
        if not config:
            config = SystemConfig(key="weekly_schedule", value=value_str)
            db.add(config)
        else:
            config.value = value_str
        db.commit()
        
        # Recarrega configurações locais
        recarregar_config()
        
        # Registra log no Guardian (se disponível)
        try:
            from services.guardian_service import guardian_instance
            guardian_instance.log_event("CONFIG_CHANGE", "Grade horária semanal atualizada pelo usuário.")
        except Exception:
            pass
            
        return {"status": "success", "message": "Grade semanal atualizada com sucesso!"}
    except Exception as e:
        db.rollback()
        logger.exception("Erro ao salvar grade semanal")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/weekly/reset")
async def reset_weekly_schedule(db: Session = Depends(get_db)):
    """Restaura a grade horária semanal para as configurações de fábrica."""
    try:
        config = db.query(SystemConfig).filter(SystemConfig.key == "weekly_schedule").first()
        value_str = json.dumps(GRADE_PADRAO, indent=4)
        if not config:
            config = SystemConfig(key="weekly_schedule", value=value_str)
            db.add(config)
        else:
            config.value = value_str
        db.commit()
        
        recarregar_config()
        return {"status": "success", "message": "Grade de fábrica restaurada com sucesso!"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
