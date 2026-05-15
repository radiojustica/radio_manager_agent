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

CACHE_STATUS = {"timestamp": 0, "payload": None}
CACHE_BUTT = {"timestamp": 0, "payload": None}
CACHE_ZARA_WINDOW = {"timestamp": 0, "status": "playing"}

def analisar_instancias_butt():
    """
    Analisa cada processo BUTT em execução. Cache de 10 segundos para evitar overhead.
    """
    agora = time.time()
    if CACHE_BUTT["payload"] and agora - CACHE_BUTT["timestamp"] < 10.0:
        return CACHE_BUTT["payload"]

    instancias = []
    # ... (rest of the code for analysis)
    # I'll rewrite it to be sure
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] and proc.info['name'].lower() == "butt.exe":
                pid = proc.info['pid']
                p = psutil.Process(pid)
                
                # CPU (amostra curta para não travar)
                cpu = p.cpu_percent(interval=0.05)
                
                # Conexões de rede
                conexoes = p.net_connections(kind='inet')
                has_connection = any(conn.status == 'ESTABLISHED' for conn in conexoes)
                
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
        except: continue
        
    CACHE_BUTT["payload"] = instancias
    CACHE_BUTT["timestamp"] = agora
    return instancias

def verificar_zara_status():
    """
    Verifica se o ZaraRadio está rodando ou travado. Cache de 5 segundos.
    """
    agora = time.time()
    if agora - CACHE_ZARA_WINDOW["timestamp"] < 5.0:
        return CACHE_ZARA_WINDOW["status"]

    from services.guardian_service import guardian_instance
    import ctypes
    
    status = "stopped"
    zara_win = guardian_instance.find_zara_window()
    if not zara_win:
        import psutil
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] and proc.info['name'].lower() == "zararadio.exe":
                status = "playing"
                break
    else:
        IsHungAppWindow = ctypes.windll.user32.IsHungAppWindow
        if bool(IsHungAppWindow(zara_win.handle)):
            status = "frozen"
        else:
            status = "playing"
            
    CACHE_ZARA_WINDOW["status"] = status
    CACHE_ZARA_WINDOW["timestamp"] = agora
    return status

@router.get("/player/now")
def get_now_playing(db: Session = Depends(get_db)):
    agora = time.time()
    # Cache de 1 segundo para maior fluidez
    if CACHE_STATUS["payload"] and agora - CACHE_STATUS["timestamp"] < 1.0:
        return CACHE_STATUS["payload"]
        
    title = "[Rádio Interrompida ou Vazia]"
    status = verificar_zara_status()
    
    butt_instances = analisar_instancias_butt()
    butt_ativos = sum(1 for b in butt_instances if b['status'] in ('transmitindo', 'conectado (ocioso?)'))
    
    if status == "playing":
        nowplaying_path = get_nowplaying_path()
        if os.path.exists(nowplaying_path):
            try:
                # ZaraRadio geralmente usa codificação cp1252 (Windows)
                with open(nowplaying_path, 'r', encoding='cp1252', errors='replace') as f:
                    content = f.read().strip()
                    if content: 
                        title = content
                    else:
                        title = "Tocando ao vivo (CurrentSong.txt vazio)"
            except Exception as e:
                import logging
                logging.getLogger("OmniCore.Status").error(f"Erro ao ler CurrentSong.txt: {e}")
        else:
            title = "Tocando ao vivo (CurrentSong.txt ausente)"
    elif status == "frozen":
        title = "[CONGELADO] ZaraRadio não está respondendo"
    elif status == "stopped":
        title = "[DESLIGADO] ZaraRadio não está em execução"

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
    
    agora = time.time()
    intervalo = agora - LAST_SHOW_WINDOW_CALL["timestamp"]
    
    if intervalo < 5:
        logger.debug(f"Show-window ignorado por debounce ({intervalo:.1f}s < 5s)")
        return {"success": False, "error": "Chamada descartada por debounce (máximo a cada 5s)"}
    
    LAST_SHOW_WINDOW_CALL["timestamp"] = agora
    
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
