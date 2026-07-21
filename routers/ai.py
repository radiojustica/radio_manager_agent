from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from core.models import Musica
from services.ai_service import ai_curator_instance

router = APIRouter(prefix="/api/ai", tags=["IA Curadoria"])

from pydantic import BaseModel
from typing import Optional, List

class BatchEnrichRequest(BaseModel):
    limit: Optional[int] = 5
    ids: Optional[List[int]] = None

@router.post("/enrich-batch")
async def enrich_batch(req: BatchEnrichRequest = None, limit: int = 5, db: Session = Depends(get_db)):
    """Dispara o processamento em lote da IA para o acervo (por IDs ou limite)."""
    selected_ids = req.ids if req and req.ids else None
    max_limit = req.limit if req and req.limit else limit
    count = ai_curator_instance.enrich_acervo_batch(db, limit=max_limit, ids=selected_ids)
    return {"status": "success", "processed": count}


@router.post("/enrich-track/{musica_id}")
async def enrich_track(musica_id: int, db: Session = Depends(get_db)):
    """Gera insight da IA para uma música específica."""
    musica = db.query(Musica).filter(Musica.id == musica_id).first()
    if not musica:
        raise HTTPException(status_code=404, detail="Música não encontrada")
        
    insight = ai_curator_instance.generate_track_intro(musica)
    musica.ai_insight = insight
    db.commit()
    
    return {"status": "success", "insight": insight}


