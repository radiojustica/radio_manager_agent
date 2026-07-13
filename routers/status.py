from fastapi import APIRouter, Depends
import os
import time
import json
import logging
from datetime import datetime
from core.time_utils import now_local

logger = logging.getLogger("OmniCore.Router.Status")
from core.database import get_db
from sqlalchemy.orm import Session
from core.models import Musica
import psutil
import win32gui
import win32process
from scripts.bulletin_sync import BulletinSync
from scripts.njud_sync import NjudSync
from scripts.giro_sync import GiroSync
from services.acervo_sync import sync_acervo

router = APIRouter(prefix="/api/status", tags=["Telemetria"])

bulletin_syncer = BulletinSync()
njud_syncer = NjudSync()
giro_syncer = GiroSync()

CACHE_STATUS = {"timestamp": 0, "payload": None}
CACHE_BUTT = {"timestamp": 0, "payload": None}
CACHE_ZARA_WINDOW = {"timestamp": 0, "status": "playing"}
LAST_SHOW_WINDOW_CALL = {"timestamp": 0}

def get_nowplaying_path():
    """Retorna o caminho do arquivo CurrentSong.txt baseado nas configurações."""
    config_path = os.path.join("config", "settings.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                log_dir = data.get("apps", {}).get("zararadio", {}).get("log_path", "D:\\RADIO\\LOG ZARARADIO")
                return os.path.join(log_dir, "CurrentSong.txt")
        except:
            pass
    return "D:\\RADIO\\LOG ZARARADIO\\CurrentSong.txt"

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
    
    # 1. Verifica se o processo do ZaraRadio está ativo no sistema operacional
    zara_process_running = False
    try:
        import psutil
        for proc in psutil.process_iter(['name']):
            try:
                if proc.name() and proc.name().lower() == "zararadio.exe":
                    zara_process_running = True
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    except Exception:
        pass

    status = "stopped"
    zara_win = guardian_instance.find_zara_window()
    is_playing = guardian_instance.is_zara_playing()
    
    if zara_process_running:
        if zara_win:
            IsHungAppWindow = ctypes.windll.user32.IsHungAppWindow
            if bool(IsHungAppWindow(zara_win.handle)):
                status = "frozen"
            else:
                status = "playing" if is_playing else "stopped"
        else:
            # Processo rodando mas janela invisível/inacessível.
            # Se is_playing foi detectado (via fallback do arquivo), é "playing", senão consideramos "playing" (como fallback seguro)
            # para evitar que o dashboard diga que o Zara não está executando.
            status = "playing" if is_playing else "playing"
    else:
        status = "stopped"
            
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
                # ZaraRadio pode gravar em UTF-8 (com ou sem BOM) ou cp1252 dependendo da versão.
                # Tentamos na ordem mais provável para evitar mojibake.
                content = None
                for enc in ("utf-8-sig", "utf-8", "cp1252"):
                    try:
                        with open(nowplaying_path, "r", encoding=enc) as f:
                            raw = f.read().strip()
                        # Teste heurístico: se o texto decodificado contiver sequências
                        # típicas de mojibake (ã, â, etc.) e o encoding for cp1252,
                        # descartamos e usamos a próxima opção.
                        if enc == "cp1252" and any(c in raw for c in ("Ã", "â€")):
                            continue
                        content = raw
                        break
                    except (UnicodeDecodeError, LookupError):
                        continue
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
        except Exception as e:
            logger.warning(f"Erro ao ler status do worker: {e}")

    # 6. Identificação de Campanha Sazonal ativa
    dt_local = now_local()
    mes_atual = dt_local.month
    dia_atual = dt_local.day
    dia_mes = (mes_atual, dia_atual)
    
    DIAS_TEMATICOS = {
        (3, 22): {"nome": "Dia Nacional do Clarone", "detalhe": "Homenagem ao mestre Pixinguinha.", "tipo": "clarone"},
        (4, 23): {"nome": "Dia Nacional do Choro", "detalhe": "Programação especial dedicada ao Choro.", "tipo": "choro"},
        (4, 30): {"nome": "Dia Internacional do Jazz", "detalhe": "Foco especial em clássicos do Jazz.", "tipo": "jazz"},
        (5, 24): {"nome": "Dia do Tecladista", "detalhe": "Destaque instrumental para Tecladistas.", "tipo": "tecladista"},
        (5, 25): {"nome": "Dia de Respeito ao Reggae", "detalhe": "Programação com destaque ao Reggae.", "tipo": "reggae"},
        (6, 14): {"nome": "Dia de Marisa Monte", "detalhe": "Especial dedicado à obra de Marisa Monte.", "tipo": "marisa_monte"},
        (7, 13): {"nome": "Dia Mundial do Rock / Cantor", "detalhe": "Programação especial: cota de 60% de Rock.", "tipo": "rock"},
        (8, 11): {"nome": "Dia Mundial do Hip-Hop", "detalhe": "Destaque especial para o Hip-Hop.", "tipo": "hiphop"},
        (8, 22): {"nome": "Dia do Folclore / Samba Brasil", "detalhe": "Programação conectada às tradições e Samba.", "tipo": "folclore"},
        (10, 17): {"nome": "Dia Nacional da MPB", "detalhe": "Dia da Música Popular Brasileira.", "tipo": "mpb"},
        (11, 22): {"nome": "Dia do Músico", "detalhe": "Homenagem a todos os músicos e instrumentistas.", "tipo": "musico"},
        (12, 2): {"nome": "Dia Nacional do Samba", "detalhe": "Especial de Samba (Tradição local em Rocas).", "tipo": "samba"},
        (12, 11): {"nome": "Dia do Tango", "detalhe": "Destaque especial para grandes tangos.", "tipo": "tango"},
        (12, 13): {"nome": "Dia Nacional do Forró", "detalhe": "Homenagem ao nascimento de Luiz Gonzaga.", "tipo": "forro"},
    }
    
    sazonalidade = {
        "ativa": False,
        "nome": "Programação Convencional",
        "detalhe": "Sem campanhas temáticas ativas no momento.",
        "tipo": "normal"
    }
    
    if dia_mes in DIAS_TEMATICOS:
        tema = DIAS_TEMATICOS[dia_mes]
        sazonalidade = {
            "ativa": True,
            "nome": tema["nome"],
            "detalhe": tema["detalhe"],
            "tipo": tema["tipo"]
        }
    elif mes_atual == 6:
        sazonalidade = {
            "ativa": True,
            "nome": "Especial Mês Junino",
            "detalhe": "Cotas de Forró, Xote e Baião ativas na grade.",
            "tipo": "junina"
        }
    elif mes_atual == 12:
        sazonalidade = {
            "ativa": True,
            "nome": "Especial de Natal",
            "detalhe": "Músicas natalinas inseridas na programação.",
            "tipo": "natal"
        }

    payload = {
        "title": title, 
        "status": status, 
        "energy": energy, 
        "butt_count": len(butt_instances),
        "butt_ativos": butt_ativos,
        "butt_detalhes": butt_instances,
        "curadoria_status": curadoria_status,
        "sazonalidade": sazonalidade,
        "updated_at": now_local().isoformat()
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
def sync_bulletins(db: Session = Depends(get_db)):
    """Dispara a sincronização manual dos boletins via GDrive."""
    res = bulletin_syncer.sync()
    from services.autopilot_service import autopilot_service
    if res.get("success", False):
        msg = f"Sincronização manual de boletins concluída. {res.get('updated', 0)} atualizações."
        autopilot_service.log_action(db, "SYNC_BULLETIN", msg, success=True)
    else:
        msg = f"Falha na sincronização manual de boletins: {res.get('error', 'Erro desconhecido')}"
        autopilot_service.log_action(db, "SYNC_BULLETIN", msg, success=False)
    return res

@router.post("/acervo/sync")
@router.post("/acervo/sync/")
def sync_acervo_endpoint(db: Session = Depends(get_db)):
    """Sincroniza o acervo de músicas a partir da pasta configurada."""
    res = sync_acervo()
    from services.autopilot_service import autopilot_service
    if "error" in res:
        msg = f"Falha na sincronização manual do acervo: {res['error']}"
        autopilot_service.log_action(db, "SYNC_ACERVO", msg, success=False)
    else:
        msg = f"Sincronização manual do acervo concluída. {res.get('inserted', 0)} faixas inseridas, {res.get('updated', 0)} atualizadas."
        autopilot_service.log_action(db, "SYNC_ACERVO", msg, success=True)
    return res

@router.get("/njud/status")
@router.get("/njud/status/")
def get_njud_status():
    """Retorna o status dos jornais locais (NJUD)."""
    return njud_syncer.get_status()

@router.post("/njud/sync")
@router.post("/njud/sync/")
def sync_njud(db: Session = Depends(get_db)):
    """Dispara a sincronização manual do NJUD (Jornais) via GDrive."""
    res = njud_syncer.sync()
    from services.autopilot_service import autopilot_service
    if res.get("success", False):
        msg = f"Sincronização manual do NJUD (Jornais) concluída. {res.get('updated', 0)} atualizações."
        autopilot_service.log_action(db, "SYNC_NJUD", msg, success=True)
    else:
        msg = f"Falha na sincronização manual do NJUD (Jornais): {res.get('error', 'Erro desconhecido')}"
        autopilot_service.log_action(db, "SYNC_NJUD", msg, success=False)
    return res

@router.get("/giro/status")
@router.get("/giro/status/")
def get_giro_status():
    """Retorna o status do Giro nas Comarcas local."""
    # Como o GiroSync não tem get_status() pronto, simulamos um simples
    target_file = os.path.join(giro_syncer.target_local_dir, "GIRO_ATUAL.mp3")
    meta_file = os.path.join(giro_syncer.target_local_dir, "GIRO_ATUAL.json")
    
    if os.path.exists(target_file):
        info = {"count": 1, "dates": ["Arquivo Presente"]}
        if os.path.exists(meta_file):
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    info["dates"] = [meta.get("date", "Data desconhecida")]
            except: pass
        return {"GIRO": info}
    return {"GIRO": {"count": 0, "dates": []}}

@router.post("/giro/sync")
@router.post("/giro/sync/")
def sync_giro(db: Session = Depends(get_db)):
    """Dispara a sincronização manual do Giro nas Comarcas via GDrive."""
    res = giro_syncer.sync()
    from services.autopilot_service import autopilot_service
    if res.get("success", False):
        msg = f"Sincronização manual do Giro concluída. {res.get('updated', 0)} atualizações."
        autopilot_service.log_action(db, "SYNC_GIRO", msg, success=True)
    else:
        msg = f"Falha na sincronização manual do Giro: {res.get('error', 'Erro desconhecido')}"
        autopilot_service.log_action(db, "SYNC_GIRO", msg, success=False)
    return res

@router.get("/logs/system")
def get_system_logs(lines: int = 50):
    """Retorna as últimas N linhas do log do sistema (omni_system.log)."""
    log_path = r"D:\RADIO\LOG ZARARADIO\omni_system.log"
    if not os.path.exists(log_path):
        return {"error": "Arquivo de log não encontrado", "path": log_path}
    
    try:
        # Usa um buffer para ler o final do arquivo de forma eficiente
        with open(log_path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            buffer_size = 1024 * 64 # 64KB
            if size < buffer_size:
                buffer_size = size
                
            f.seek(-buffer_size, os.SEEK_END)
            content = f.read().decode("utf-8", errors="replace")
            last_lines = content.splitlines()[-lines:]
            
            return {
                "path": log_path,
                "lines": last_lines,
                "total_size_mb": round(size / (1024*1024), 2)
            }
    except Exception as e:
        return {"error": str(e)}
