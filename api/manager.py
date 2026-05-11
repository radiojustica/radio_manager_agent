import logging
import os
import socket
import subprocess
import sys
import time
from datetime import datetime
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
from worker_manager import worker_manager_instance
from routers import acervo, status, config, ai, workers, engine as engine_router
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
            except:
                pass

manager = ConnectionManager()

@app.websocket("/ws/status")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Loop para manter a conexão aberta e enviar atualizações periódicas
        while True:
            # Coleta dados atuais
            from routers.status import analisar_instancias_butt, get_zara_status
            from services.guardian_service import guardian_instance
            
            data = {
                "player": get_zara_status(),
                "events": guardian_instance.events_list[:10],
                "timestamp": datetime.now().strftime('%H:%M:%S')
            }
            await websocket.send_text(json.dumps(data))
            await asyncio.sleep(2) # Atualiza a cada 2 segundos
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ... (restante do arquivo)

BASE_PATH = Path(__file__).resolve().parent.parent
FRONTEND_PATH = BASE_PATH / "frontend" / "dist"

Base.metadata.create_all(bind=engine)

app.include_router(acervo.router)
app.include_router(status.router)
app.include_router(config.router)
app.include_router(ai.router)
app.include_router(workers.router)
app.include_router(engine_router.router)
app.include_router(downloader_router)

@app.on_event("startup")
def startup_event() -> None:
    logger.info("API startup: iniciando orquestrador de workers...")
    worker_manager_instance.start_orchestrator()

@app.on_event("shutdown")
def shutdown_event() -> None:
    logger.info("API shutdown: interrompendo orquestrador de workers...")
    worker_manager_instance.stop_orchestrator()

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
            f.write(f"{datetime.now()} - {error_msg}\n")

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