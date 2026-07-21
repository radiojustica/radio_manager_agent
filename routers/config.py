from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
import json
import os
import shutil

from pathlib import Path
from core.path_utils import safe_path

router = APIRouter(prefix="/api/config", tags=["Configurações"])

CONFIG_FILE = "config/settings.json"

@router.get("/badwords")
async def get_badwords():
    badwords_path = "config/badwords.json"
    if not os.path.exists(badwords_path):
        default = ["puta", "safadao", "baroes da pisadinha"]
        with open(badwords_path, "w", encoding="utf-8") as f:
            json.dump(default, f)
    
    with open(badwords_path, "r", encoding="utf-8") as f:
        return json.load(f)

from pydantic import BaseModel
from core.models import RegraProgramacao

class RuleSchema(BaseModel):
    bloco: str
    energia_alvo: int

@router.post("/schedule")
async def save_schedule_rules(rules: list[RuleSchema], db: Session = Depends(get_db)):
    try:
        for rule in rules:
            db_rule = db.query(RegraProgramacao).filter(RegraProgramacao.bloco == rule.bloco).first()
            if db_rule:
                db_rule.energia_alvo = rule.energia_alvo
            else:
                db.add(RegraProgramacao(bloco=rule.bloco, energia_alvo=rule.energia_alvo))
        db.commit()
        return {"status": "success", "message": "Regras salvas com sucesso"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/schedule")
async def get_schedule_rules(db: Session = Depends(get_db)):
    rules = db.query(RegraProgramacao).all()
    if not rules:
        return [
            {"bloco": "Madrugada", "energia_alvo": 2},
            {"bloco": "Manhã", "energia_alvo": 4},
            {"bloco": "Tarde", "energia_alvo": 5},
            {"bloco": "Noite", "energia_alvo": 3},
        ]
    return [{"bloco": r.bloco, "energia_alvo": r.energia_alvo} for r in rules]


@router.get("/grade")
async def get_grade():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("grade", {})
    return {}

@router.post("/grade")
async def save_grade(grade_data: dict):
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["grade"] = grade_data
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return {"status": "success"}
    return {"status": "error", "message": "Settings file not found"}

@router.get("/quarantine/logs")
async def get_quarantine_logs():
    log_path = r"D:\RADIO\QUARENTENA_TJ\audit_quarentena.log"
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            return f.readlines()[-100:]
    return []

@router.get("/quarantine/files")
async def get_quarantine_files():
    folder = r"D:\RADIO\QUARENTENA_TJ"
    if os.path.exists(folder):
        return [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f)) and not f.endswith('.log')]
    return []

@router.post("/quarantine/restore")
async def restore_quarantine_file(filename: str, db: Session = Depends(get_db)):
    from core.models import Musica
    try:
        source = safe_path(Path(r"D:\RADIO\QUARENTENA_TJ"), filename)
        target = safe_path(Path(r"D:\RADIO\MUSICAS"), filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    if os.path.exists(source):
        try:
            shutil.move(str(source), str(target))
            
            # Blindagem no Banco: Marca como auditado e remove redflag
            musica = db.query(Musica).filter(Musica.caminho.ilike(f"%{filename}")).first()
            if musica:
                musica.auditado_acustica = True
                musica.redflag = False
                db.commit()
                
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    return {"status": "error", "message": "File not found"}


