import os
import json
import time
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger("OmniCore.Programacao")
router = APIRouter(prefix="/api/programacao", tags=["Programacao"])

_PROG_DIR = r"D:\RADIO\PROGRAMACAO"
_LOG_DIR_DEFAULT = r"D:\RADIO\LOG ZARARADIO"

# mapeamento hora->arquivo m3u por faixa de 2h
HORA_M3U = {
    0: "PROG_00H.m3u", 2: "PROG_02H.m3u", 4: "PROG_04H.m3u",
    6: "PROG_06H.m3u", 8: "PROG_08H.m3u", 10: "PROG_10H.m3u",
    12: "PROG_12H.m3u", 14: "PROG_14H.m3u", 16: "PROG_16H.m3u",
    18: "PROG_18H.m3u", 20: "PROG_20H.m3u", 22: "PROG_22H.m3u",
}

class FilaResponse(BaseModel):
    current_index: int
    current: dict | None
    next: list[dict]
    m3u: str
    total: int
    updated_at: str

def _m3u_path_for_now() -> tuple[str, str]:
    now = datetime.now()
    # horário de natal/rn
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("America/Fortaleza")
        now = datetime.now(tz)
    except Exception:
        now = datetime.now()

    hora = (now.hour // 2) * 2
    nome = HORA_M3U.get(hora, f"PROG_{hora:02d}H.m3u")
    return os.path.join(_PROG_DIR, nome), nome

def _nowplaying_path() -> str:
    cfg = "config/settings.json"
    try:
        with open(cfg, "r", encoding="utf-8") as f:
            data = json.load(f)
        log_dir = data.get("apps", {}).get("zararadio", {}).get("log_path", _LOG_DIR_DEFAULT)
        return os.path.join(log_dir, "CurrentSong.txt")
    except Exception:
        return os.path.join(_LOG_DIR_DEFAULT, "CurrentSong.txt")

def _read_m3u(path: str) -> list[str]:
    if not os.path.exists(path):
        return []
    try:
        lines = []
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for raw in f:
                s = raw.strip()
                if not s:
                    continue
                if s.startswith("#"):
                    continue
                lines.append(s)
        return lines
    except Exception:
        return []

def _nome_arquivo(caminho: str) -> str:
    try:
        return os.path.splitext(os.path.basename(caminho))[0]
    except Exception:
        return str(caminho)

CACHE_FILA = {"timestamp": 0, "payload": None}

@router.get("/fila", response_model=FilaResponse)
def get_fila():
    agora = time.time()
    if CACHE_FILA["payload"] and agora - CACHE_FILA["timestamp"] < 5.0:
        return CACHE_FILA["payload"]

    m3u_path, m3u_name = _m3u_path_for_now()
    files = _read_m3u(m3u_path)

    now_title = ""
    np_path = _nowplaying_path()
    if os.path.exists(np_path):
        try:
            for enc in ("utf-8-sig", "utf-8", "cp1252"):
                try:
                    with open(np_path, "r", encoding=enc) as f:
                        now_title = f.read().strip()
                    break
                except Exception:
                    continue
            if not now_title:
                now_title = ""
        except Exception:
            now_title = ""
    else:
        now_title = ""

    now_title_norm = now_title.replace(".mp3", "").strip().lower()

    current_index = -1
    for idx, caminho in enumerate(files):
        nome = _nome_arquivo(caminho)
        if nome.lower() == now_title_norm or now_title_norm in nome.lower() or nome.lower() in now_title_norm:
            if abs(len(nome) - len(now_title_norm)) <= 8 or len(now_title_norm) >= 6:
                current_index = idx
                break

    if current_index == -1 and files:
        current_index = 0

    current = None
    if current_index >= 0 and current_index < len(files):
        caminho = files[current_index]
        current = {
            "index": current_index,
            "titulo": _nome_arquivo(caminho),
            "caminho": caminho,
            "duracao": 0,
            "artista": "ZaraRadio",
        }

    prox = []
    start = current_index + 1
    for idx in range(start, min(start + 8, len(files))):
        prox.append({
            "index": idx,
            "titulo": _nome_arquivo(files[idx]),
            "caminho": files[idx],
            "duracao": 0,
            "artista": "",
        })

    payload = {
        "current_index": current_index,
        "current": current,
        "next": prox,
        "m3u": m3u_name,
        "total": len(files),
        "updated_at": datetime.now(timezone(timedelta(hours=-3))).isoformat(),
    }
    CACHE_FILA["timestamp"] = time.time()
    CACHE_FILA["payload"] = payload
    return payload
