import logging
import os
import socket
import subprocess
import sys
import time
from datetime import datetime
from core.time_utils import now_local, now_utc
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import asyncio
import json

from core.database import engine, Base, SessionLocal
from core.models import RegraProgramacao
from routers import acervo, status, config, ai, workers, engine as engine_router, reports
from routers.downloader import router as downloader_router

logger = logging.getLogger("OmniCore.APIManager")

app = FastAPI(title="Omni Core V2", version="2.0.0", redirect_slashes=True)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class RuleSchema(BaseModel):
    bloco: str
    energia_alvo: int

@app.post("/api/config/schedule")
async def save_schedule_rules(rules: list[RuleSchema]):
    db = SessionLocal()
    try:
        for rule in rules:
            db_rule = db.query(RegraProgramacao).filter(RegraProgramacao.bloco == rule.bloco).first()
            if db_rule:
                db_rule.energia_alvo = rule.energia_alvo
            else:
                db.add(RegraProgramacao(bloco=rule.bloco, energia_alvo=rule.energia_alvo))
        db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()

# Gerenciador de conexões WebSocket
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass

manager = ConnectionManager()

async def broadcast_event(event: dict):
    """Envia um evento para todos os clientes WebSocket conectados de forma assíncrona."""
    # Como o broadcast_event pode ser chamado de threads síncronas (workers),
    # precisamos garantir que ele rode no loop de eventos do FastAPI se necessário.
    message = json.dumps(event)
    for connection in manager.active_connections:
        try:
            # Usamos call_soon_threadsafe se não estivermos na mesma thread, 
            # mas aqui assumimos que será chamado via async onde possível.
            await connection.send_text(message)
        except Exception:
            pass

@app.websocket("/ws/status")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Loop passivo: apenas mantém a conexão viva e envia heartbeats
        while True:
            # Heartbeat para evitar timeout do browser/proxy
            await websocket.send_text(json.dumps({"type": "heartbeat", "timestamp": now_utc().isoformat()}))
            await asyncio.sleep(30) 
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Erro no WebSocket: {e}")
        manager.disconnect(websocket)

BASE_PATH = Path(__file__).resolve().parent.parent

@app.get("/api/status/logs/system")
async def get_system_logs():
    """Lê as últimas 50 linhas do log do sistema de forma eficiente."""
    log_file = BASE_PATH / "logs" / "omni_system.log"
    if not log_file.exists():
        return {"logs": ["Log file not found."]}
    
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            # Lendo as últimas 50 linhas
            lines = f.readlines()
            return {"logs": [line.strip() for line in lines[-50:]]}
    except Exception as e:
        return {"logs": [f"Error reading logs: {str(e)}"]}

FRONTEND_PATH = BASE_PATH / "frontend" / "dist"

Base.metadata.create_all(bind=engine)

app.include_router(acervo.router)
app.include_router(status.router)
app.include_router(config.router)
app.include_router(ai.router)
app.include_router(workers.router)
app.include_router(reports.router)
app.include_router(engine_router.router)
app.include_router(downloader_router)

if FRONTEND_PATH.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_PATH), html=True), name="static")
else:
    logger.warning(f"Diretório do frontend não encontrado: {FRONTEND_PATH}")

    @app.get("/")
    async def root():
        return {"status": "Online", "dashboard_url": "http://localhost:8001"}


def run_api_server():
    """Executa o servidor FastAPI com log de erros robusto."""
    try:
        logger.info("Tentando subir servidor uvicorn na porta 8001...")
        uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info", log_config=None)
    except Exception as e:
        error_msg = f"ERRO CRÍTICO NO UVICORN: {e}"
        if "10048" in str(e) or "already in use" in str(e).lower():
            error_msg = "ERRO: A porta 8001 já está em uso por outro programa. O Dashboard não ficará disponível."
        
        logger.error(error_msg)
        exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd()
        with open(os.path.join(exe_dir, "fastapi_crash.log"), "a", encoding="utf-8") as f:
            f.write(f"{now_local()} - {error_msg}\n")

def wait_for_server(host="127.0.0.1", port=8001, timeout=30):
    """Aguarda até que o servidor web esteja aceitando conexões."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except Exception:
            time.sleep(0.5)
    return False
