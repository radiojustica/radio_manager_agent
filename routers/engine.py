"""
Router: Engine — Omni Core V2
==============================
Endpoints para geração de grade musical e consulta de regras.

Regras de negócio ficam em grade_rules.py.
Orquestração de geração fica em playlist_engine.py.
Este router apenas expõe a API HTTP.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from director.playlist_engine import playlist_engine_instance
from director.actor_critic import actor_critic_instance
from core.models import Musica
from sqlalchemy import func
from director import grade_rules as GR
from services import weather_service
import psutil
from core import state
import os
from scripts.streaming_stats import StreamingStats

router = APIRouter(prefix="/api/engine", tags=["Engine"])

# Configuração fictícia de streaming (no futuro virá do settings.json)
streaming_stats = StreamingStats({
    "enabled": True,
    "server_type": "icecast",
    "url": "http://localhost:8000/status-json.xsl",
    "mount": "/stream"
})

# ---------------------------------------------------------------------------
# Estatísticas do acervo
# ---------------------------------------------------------------------------

@router.get("/stats")
def get_engine_stats(full: bool = False, db: Session = Depends(get_db)):
    """Retorna estatísticas detalhadas do acervo com detecção de rede."""
    total    = db.query(Musica).count()
    auditadas = db.query(Musica).filter(Musica.auditado_acustica == True).count()
    redflags  = db.query(Musica).filter(Musica.redflag == True).count()

    # Tempo total do acervo (em segundos -> horas)
    tempo_total_s = db.query(func.sum(Musica.duracao)).scalar() or 0
    tempo_total_h = round(tempo_total_s / 3600, 1)

    # Top estilos
    limit_estilos = 20 if full else 5
    estilos = (
        db.query(Musica.estilo, func.count(Musica.id))
        .group_by(Musica.estilo)
        .order_by(func.count(Musica.id).desc())
        .limit(limit_estilos)
        .all()
    )

    # Top Artistas (Representatividade)
    limit_artistas = 10 if full else 5
    artistas = (
        db.query(Musica.artista, func.count(Musica.id))
        .filter(Musica.artista != "VARIOUS", Musica.artista != "Desconhecido")
        .group_by(Musica.artista)
        .order_by(func.count(Musica.id).desc())
        .limit(limit_artistas)
        .all()
    )

    # Distribuição de energia
    energias = db.query(Musica.energia, func.count(Musica.id)).group_by(Musica.energia).all()
    energia_dist = {str(i): 0 for i in range(1, 6)}
    for e in energias:
        key = str(e[0]) if e[0] and 1 <= e[0] <= 5 else "3"
        energia_dist[key] += e[1]

    # Saúde do sistema
    mem = psutil.virtual_memory()
    servidor_online = os.path.exists(r"D:\SERVIDOR\BOLETINS")

    health = {
        "cpu": psutil.cpu_percent(),
        "ram_percent": mem.percent,
        "ram_free_mb": int(mem.available / (1024 * 1024)),
        "network_online": servidor_online
    }

    try:
        clima = weather_service.get_natal_weather_mood()
    except:
        clima = "Ensolarado"

    listeners = streaming_stats.get_listeners()

    return {
        "total":       total,
        "auditadas":   auditadas,
        "pendentes":   total - auditadas,
        "redflags":    redflags,
        "tempo_total_h": tempo_total_h,
        "top_estilos": [{"nome": e[0].title() if e[0] else "Sem Estilo", "qtd": e[1]} for e in estilos],
        "top_artistas": [{"nome": a[0], "qtd": a[1]} for a in artistas],
        "energia_dist": energia_dist,
        "clima_natal": clima,
        "health":      health,
        "listeners":   listeners,
        "is_full": full
    }


# ---------------------------------------------------------------------------
# Regras ativas (novo)
# ---------------------------------------------------------------------------

@router.get("/regras")
def get_regras():
    """Retorna as regras e configurações de grade atualmente ativas.

    Útil para o Dashboard exibir quais MOODS/estilos e intervalos estão em uso.
    Também recarrega as configurações de settings.json antes de responder.
    """
    GR.recarregar_config()
    return GR.regras_ativas()


# ---------------------------------------------------------------------------
# Geração de grade
# ---------------------------------------------------------------------------

@router.post("/gerar-24h")
def trigger_24h(mood: str = "Ensolarado"):
    """Gera manualmente a programação completa de 24h (12 blocos de 2h)."""
    ok = playlist_engine_instance.gerar_programacao_diaria(mood)
    if ok:
        return {"status": "success", "message": f"Programação 24h gerada (Mood: {mood})."}
    raise HTTPException(status_code=500, detail="Falha ao gerar programação 24h.")


@router.post("/gerar-extra")
def trigger_extra(mood: str = "Ensolarado"):
    """Gera manualmente o Bloco Extra para cobrir o horário restante do bloco atual."""
    ok = playlist_engine_instance.gerar_bloco_extra(mood)
    if ok:
        return {"status": "success", "message": "Bloco Extra gerado com sucesso."}
    raise HTTPException(status_code=500, detail="Falha ao gerar Bloco Extra.")


@router.post("/gerar-24h-llm")
def trigger_24h_llm(mood: str = "Ensolarado"):
    """Gera manualmente a programação completa de 24h usando o fluxo Actor-Critic."""
    ok = playlist_engine_instance.gerar_programacao_diaria_llm(mood)
    if ok:
        return {"status": "success", "message": f"Programação 24h LLM gerada (Mood: {mood})."}
    raise HTTPException(status_code=500, detail="Falha ao gerar programação 24h LLM.")


@router.post("/gerar-bloco-llm")
def trigger_bloco_llm(hora_inicio: int, mood: str = "Ensolarado"):
    """Gera manualmente um bloco de 2h usando o fluxo Actor-Critic."""
    ok = playlist_engine_instance.gerar_playlist_bloco_llm(hora_inicio, mood)
    if ok:
        return {"status": "success", "message": f"Bloco LLM {hora_inicio:02d}H gerado com sucesso."}
    raise HTTPException(status_code=500, detail=f"Falha ao gerar bloco LLM {hora_inicio:02d}H.")


@router.get("/llm-memory")
def get_llm_memory():
    """Retorna o histórico de memória e score do fluxo Actor-Critic."""
    return actor_critic_instance.memory_summary()


@router.post("/recarregar-regras")
def recarregar_regras():
    """Recarrega as regras de grade de settings.json sem reiniciar o sistema."""
    cfg = GR.recarregar_config()
    return {"status": "success", "config_recarregada": cfg}


