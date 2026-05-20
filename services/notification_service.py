import requests
import logging
import os
import json
from pathlib import Path

logger = logging.getLogger("OmniCore.NotificationService")

def _load_whatsapp_config():
    """Carrega a configuração de WhatsApp do settings.json."""
    settings_path = Path(__file__).resolve().parent.parent / "config" / "settings.json"
    if settings_path.exists():
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("notifications", {}).get("whatsapp", {})
        except Exception as e:
            logger.error(f"Erro ao carregar settings.json no NotificationService: {e}")
    return {}

def send_whatsapp_alert(message: str):
    """
    Envia um alerta de WhatsApp usando o provedor configurado (Evolution ou Z-API).
    Mantém compatibilidade com a chamada legada.
    """
    lock_file = os.path.join(os.getcwd(), "mute_whatsapp.lock")
    if os.path.exists(lock_file):
        return

    config = _load_whatsapp_config()
    if not config.get("enabled", False):
        # Fallback para CallMeBot se estiver configurado mas o novo estiver desativado?
        # Melhor não, vamos forçar o novo padrão.
        logger.warning("WhatsApp Notifications desativadas no settings.json")
        return

    provider = config.get("provider", "evolution").lower()
    target = config.get("target_number")
    
    if not target:
        logger.error("Número de destino não configurado no settings.json")
        return

    try:
        if provider == "evolution":
            _send_via_evolution(config, target, message)
        elif provider == "zapi":
            _send_via_zapi(config, target, message)
        else:
            logger.error(f"Provedor de WhatsApp desconhecido: {provider}")
    except Exception as e:
        logger.error(f"Erro crítico ao enviar notificação WhatsApp: {e}")

def _send_via_evolution(config, number, text):
    evol_cfg = config.get("evolution", {})
    url_base = evol_cfg.get("url")
    instance = evol_cfg.get("instance")
    apikey = evol_cfg.get("apikey")
    
    if not all([url_base, instance, apikey]):
        logger.error("Configuração da Evolution API incompleta.")
        return
        
    url = f"{url_base.rstrip('/')}/message/sendText/{instance}"
    headers = {"apikey": apikey, "Content-Type": "application/json"}
    payload = {
        "number": number,
        "options": {"delay": 1200, "presence": "composing", "linkPreview": False},
        "textMessage": {"text": text}
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=10)
    if response.status_code in (200, 201):
        logger.info(f"Notificação enviada via Evolution para {number}")
    else:
        logger.error(f"Falha na Evolution API: {response.status_code} - {response.text}")

def _send_via_zapi(config, number, text):
    zapi_cfg = config.get("zapi", {})
    instance_id = zapi_cfg.get("instance_id")
    token = zapi_cfg.get("token")
    
    if not all([instance_id, token]):
        logger.error("Configuração da Z-API incompleta.")
        return
        
    url = f"https://api.z-api.io/instances/{instance_id}/token/{token}/send-text"
    payload = {"phone": number, "message": text}
    
    response = requests.post(url, json=payload, timeout=10)
    if response.status_code in (200, 201):
        logger.info(f"Notificação enviada via Z-API para {number}")
    else:
        logger.error(f"Falha na Z-API: {response.status_code} - {response.text}")

async def send_whatsapp_notification(message: str):
    """Wrapper assíncrono para compatibilidade."""
    send_whatsapp_alert(message)
