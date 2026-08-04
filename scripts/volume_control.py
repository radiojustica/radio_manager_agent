"""
volume_control.py — Ajuste MANUAL de volume via comando remoto (ntfy).

⚠️ IMPORTANTE — SEGURANÇA ACÚSTICA:
Este módulo NUNCA é chamado pelo monitor/autopilot automático.
É acionado SOMENTE por um comando explícito do operador ("volume 80%").
O sistema automático (core/monitor.py, scripts/audio_manager.py) continua
ESTRITAMENTE somente-leitura e nunca altera volume por conta própria.
"""
import logging
import re

try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
    import ctypes
    _HAS_PYCAW = True
except Exception:
    _HAS_PYCAW = False

logger = logging.getLogger("OmniCore.VolumeControl")

# Dispositivo de transmissão: placa USB Audio CODEC que o Windows rotula como
# "INTERNO (2- USB Audio CODEC)". Por isso buscamos por ambos os termos.
DEVICE_KEYWORDS = ["usb audio codec", "interno"]


def parse_volume_command(text: str):
    """
    Retorna um float 0.0–1.0 se `text` for um comando de volume válido,
    ou None caso contrário.
    Aceita: "volume 80%", "volume 80", "volume 0.8", "vol 50%", "abaixar volume 30".
    """
    if not text:
        return None
    t = text.lower()
    if not ("volume" in t or "vol " in t or t.strip().startswith("vol")):
        return None
    m = re.search(r"(\d{1,3})\s*%?", t)
    if not m:
        return None
    value = int(m.group(1))
    if value > 100:
        value = 100
    if value < 0:
        value = 0
    return value / 100.0


def set_usb_device_volume(level: float) -> dict:
    """
    Define o volume MASTER da placa USB de transmissão ("RADIO").
    level: 0.0–1.0. Retorna dicionário com status/resultado.
    """
    if not _HAS_PYCAW:
        return {"success": False, "error": "pycaw indisponível neste ambiente."}

    try:
        devices = AudioUtilities.GetAllDevices()
        target = None
        # Prioriza correspondência exata "usb audio codec", depois "interno"
        for kw in DEVICE_KEYWORDS:
            for d in devices:
                try:
                    if kw in (d.FriendlyName or "").lower():
                        target = d
                        break
                except Exception:
                    continue
            if target:
                break
        if not target:
            # fallback: dispositivo de saída padrão
            target = AudioUtilities.GetSpeakers()

        endpoint = target.Activate(
            IAudioEndpointVolume._iid_, CLSCTX_ALL, None
        ).QueryInterface(IAudioEndpointVolume)

        # pycaw expõe SetMasterVolumeLevelScalar(0..1, None)
        endpoint.SetMasterVolumeLevelScalar(float(level), None)
        actual = endpoint.GetMasterVolumeLevelScalar()
        pct = int(round(actual * 100))
        logger.info("[VOLUME] Volume da placa USB definido para %d%% (requisição do operador).", pct)
        return {"success": True, "level": actual, "percent": pct}
    except Exception as e:
        logger.error("[VOLUME] Falha ao ajustar volume: %s", e)
        return {"success": False, "error": str(e)}
