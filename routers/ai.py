from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from core.models import Musica
from services.ai_service import ai_curator_instance

router = APIRouter(prefix="/api/ai", tags=["IA Curadoria"])

@router.post("/enrich-batch")
async def enrich_batch(limit: int = 5, db: Session = Depends(get_db)):
    """Dispara o processamento em lote da IA para o acervo."""
    count = ai_curator_instance.enrich_acervo_batch(db, limit)
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


