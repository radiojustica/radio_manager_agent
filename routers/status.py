from fastapi import APIRouter, Depends
import os
import time
from datetime import datetime
from core.database import get_db
from sqlalchemy.orm import Session
from core.models import Musica
import psutil
import win32gui
import win32process
from scripts.bulletin_sync import BulletinSync

router = APIRouter(prefix="/api/status", tags=["Telemetria"])

bulletin_syncer = BulletinSync()

NOWPLAYING_PATH = r"D:\RADIO\LOG ZARARADIO\CurrentSong.txt"
CACHE_STATUS = {"timestamp": 0, "payload": None}

# Debounce para evitar chamadas repetidas ao show-window
LAST_SHOW_WINDOW_CALL = {"timestamp": 0}

def analisar_instancias_butt():
    """
    Analisa cada processo BUTT em execução e retorna uma lista de dicionários
    com informações detalhadas sobre seu estado.
    """
    instancias = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] and proc.info['name'].lower() == "butt.exe":
                pid = proc.info['pid']
                p = psutil.Process(pid)
                
                # CPU (amostra de 100ms)
                cpu = p.cpu_percent(interval=0.1)
                
                # Conexões de rede estabelecidas
                conexoes = p.net_connections(kind='inet')
                has_connection = any(conn.status == 'ESTABLISHED' for conn in conexoes)
                
                # Título da janela
                window_title = "Desconhecido"
                def enum_callback(hwnd, hwnd_list):
                    if win32gui.IsWindowVisible(hwnd):
                        _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
                        if found_pid == pid:
                            title = win32gui.GetWindowText(hwnd)
                            if title: hwnd_list.append(title)
                hwnd_list = []
                win32gui.EnumWindows(enum_callback, hwnd_list)
                if hwnd_list: window_title = hwnd_list[0]
                
                # Heurística de status
                if has_connection and cpu > 0.5:
                    status = "transmitindo"
                elif has_connection and cpu <= 0.5:
                    status = "conectado (ocioso?)"
                elif not has_connection and cpu < 0.5:
                    status = "parado"
                else:
                    status = "indeterminado"
                
                if "disconnected" in window_title.lower():
                    status = "desconectado"
                elif "connected" in window_title.lower():
                    if status == "parado": status = "conectado (não transmitindo?)"
                
                instancias.append({
                    "pid": pid,
                    "status": status,
                    "cpu": round(cpu, 1),
                    "has_connection": has_connection,
                    "window_title": window_title[:50]
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return instancias

def verificar_zara_processos_hung():
    import psutil
    import ctypes
    rodando = False
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] and proc.info['name'].lower() == "zararadio.exe":
            rodando = True
            break
    if not rodando: return "stopped"
    
    IsHungAppWindow = ctypes.windll.user32.IsHungAppWindow
    zara_hwnd = None
    def find_zara(hwnd, lParam):
        nonlocal zara_hwnd
        if "ZaraRadio" in win32gui.GetWindowText(hwnd):
            zara_hwnd = hwnd
            return False
        return True
    win32gui.EnumWindows(find_zara, 0)
    if zara_hwnd and bool(IsHungAppWindow(zara_hwnd)): return "frozen"
    return "playing"

@router.get("/player/now")
def get_now_playing(db: Session = Depends(get_db)):
    agora = time.time()
    if CACHE_STATUS["payload"] and agora - CACHE_STATUS["timestamp"] < 2.0:
        return CACHE_STATUS["payload"]
        
    title = "[Rádio Interrompida ou Vazia]"
    status = verificar_zara_processos_hung()
    
    butt_instances = analisar_instancias_butt()
    butt_ativos = sum(1 for b in butt_instances if b['status'] in ('transmitindo', 'conectado (ocioso?)'))
    
    if status == "playing":
        if os.path.exists(NOWPLAYING_PATH):
            try:
                # ZaraRadio geralmente usa codificação cp1252 (Windows)
                with open(NOWPLAYING_PATH, 'r', encoding='cp1252', errors='replace') as f:
                    content = f.read().strip()
                    if content: title = content
            except: pass
        else:
            title = "Tocando ao vivo (CurrentSong.txt ausente)"
    
    energy = 0.5
    clean_title = title.replace(".mp3", "").strip()
    faixa_db = db.query(Musica).filter(Musica.caminho.ilike(f"%{clean_title}%")).first()
    if faixa_db: energy = faixa_db.energia / 5.0
        
    curadoria_status = "Ocioso"
    status_file = os.path.join(os.path.dirname(__file__), "..", "worker_status.txt")
    if os.path.exists(status_file):
        try:
            with open(status_file, "r", encoding="utf-8") as f:
                curadoria_status = f.read().strip()
        except: pass

    payload = {
        "title": title, 
        "status": status, 
        "energy": energy, 
        "butt_count": len(butt_instances),
        "butt_ativos": butt_ativos,
        "butt_detalhes": butt_instances,
        "curadoria_status": curadoria_status,
        "updated_at": datetime.now().isoformat()
    }
    CACHE_STATUS["payload"] = payload
    CACHE_STATUS["timestamp"] = agora
    return payload

@router.post("/butt/reconnect")
def force_butt_reconnect():
    """Força a tentativa de reconexão de todas as instâncias do BUTT paradas."""
    try:
        from services.guardian_service import guardian_instance
        reconectados, total = guardian_instance.reconnect_idle_butts()
        return {"success": True, "reconnected": reconectados, "total": total}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/player/force_play")
def force_zara_play():
    """Força o play no ZaraRadio (atalho P)."""
    from services.guardian_service import guardian_instance
    result = guardian_instance.force_play()
    return {"success": result}

@router.get("/guardian/events")
def get_guardian_events(limit: int = 5):
    from services.guardian_service import guardian_instance
    return {"events": guardian_instance.events[:limit]}

@router.post("/system/show-window")
def show_backend_window():
    """Aciona o callback para mostrar a janela do backend (com debounce de 5s)."""
    from core import state
    import logging
    logger = logging.getLogger("OmniCore.Status")
    
    # Debounce: não permite chamadas mais frequentes que a cada 5 segundos
    agora = time.time()
    intervalo = agora - LAST_SHOW_WINDOW_CALL["timestamp"]
    
    if intervalo < 5:  # Menos de 5 segundos desde a última chamada
        logger.debug(f"Show-window ignorado por debounce ({intervalo:.1f}s < 5s)")
        return {"success": False, "error": "Chamada descartada por debounce (máximo a cada 5s)"}
    
    LAST_SHOW_WINDOW_CALL["timestamp"] = agora
    
    logger.info(f"Requisição para mostrar janela do backend. Callback status: {'Registrado' if state.SHOW_UI_CALLBACK else 'Nulo'}")
    
    if state.SHOW_UI_CALLBACK:
        try:
            state.SHOW_UI_CALLBACK()
            return {"success": True}
        except Exception as e:
            logger.error(f"Erro ao executar SHOW_UI_CALLBACK: {e}")
            return {"success": False, "error": str(e)}
            
    return {"success": False, "error": "Callback não registrado"}

@router.get("/bulletins/status")
@router.get("/bulletins/status/")
def get_bulletins_status():
    """Retorna o status dos boletins locais."""
    return bulletin_syncer.get_status()

@router.post("/bulletins/sync")
@router.post("/bulletins/sync/")
def sync_bulletins():
    """Dispara a sincronização manual dos boletins via GDrive."""
    return bulletin_syncer.sync()


