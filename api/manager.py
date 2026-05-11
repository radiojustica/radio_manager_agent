import logging
import os
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

from core.database import engine, Base
from worker_manager import worker_manager_instance
from routers import acervo, status, config, ai, workers, engine as engine_router
from routers.downloader import router as downloader_router

logger = logging.getLogger("OmniCore.APIManager")

BASE_PATH = Path(__file__).resolve().parent.parent
FRONTEND_PATH = BASE_PATH / "frontend" / "dist"

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Omni Core V2", version="2.0.0", redirect_slashes=True)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

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