import logging
import requests
from typing import Any
from core.worker_base import WorkerBase, WorkerResult
from core.reward import RewardStore

logger = logging.getLogger("OmniCore.Workers.Notification")

class NotificationWorker(WorkerBase):
    """
    Worker responsável pela gestão de notificações e alertas do sistema.
    Focado em WhatsApp (Evolution/Z-API) e logs de eventos críticos.
    """
    def __init__(self, reward_store: RewardStore | None = None, config: dict[str, Any] | None = None):
        super().__init__(name="NotificationWorker", reward_store=reward_store, config=config)
        
        # Carregamos as configurações globais de notificações do settings.json
        from pathlib import Path
        import json
        
        self.notif_config = {}
        settings_path = Path(__file__).resolve().parent.parent / "config" / "settings.json"
        
        if settings_path.exists():
            try:
                with open(settings_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.notif_config = data.get("notifications", {}).get("whatsapp", {})
            except Exception as e:
                self.log_error(e, "LOAD_SETTINGS_FAILED")

    def send_whatsapp(self, message: str) -> bool:
        """Envia mensagem via WhatsApp usando o provedor configurado."""
        if not self.notif_config.get("enabled", False):
            self.log_action("SEND_WHATSAPP_DISABLED", message=message[:50])
            return False

        provider = self.notif_config.get("provider", "evolution").lower()
        target = self.notif_config.get("target_number")
        
        if not target:
            self.log_action("MISSING_TARGET_NUMBER", level="warning")
            return False
        
        try:
            if provider == "evolution":
                return self._send_evolution(target, message)
            elif provider == "zapi":
                return self._send_zapi(target, message)
            else:
                self.log_error(ValueError(f"Provedor desconhecido: {provider}"), "WHATSAPP_SEND_FAILED")
                return False
        except Exception as e:
            self.log_error(e, "WHATSAPP_SEND_EXCEPTION")
            return False

    def _send_evolution(self, number: str, text: str) -> bool:
        evol_cfg = self.notif_config.get("evolution", {})
        url_base = evol_cfg.get("url")
        instance = evol_cfg.get("instance")
        apikey = evol_cfg.get("apikey")
        
        if not all([url_base, instance, apikey]):
            self.log_action("EVOLUTION_CONFIG_MISSING", level="warning")
            return False
            
        url = f"{url_base.rstrip('/')}/message/sendText/{instance}"
        headers = {"apikey": apikey, "Content-Type": "application/json"}
        
        # Payload padrão para Evolution API v1.x/2.x
        payload = {
            "number": number,
            "options": {"delay": 1200, "presence": "composing", "linkPreview": False},
            "textMessage": {"text": text}
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        if response.status_code in (200, 201):
            self.log_action("WHATSAPP_SENT_EVOLUTION", target=number)
            return True
        else:
            self.log_action("WHATSAPP_FAILED_EVOLUTION", status=response.status_code, response=response.text[:100])
            return False

    def _send_zapi(self, number: str, text: str) -> bool:
        zapi_cfg = self.notif_config.get("zapi", {})
        instance_id = zapi_cfg.get("instance_id")
        token = zapi_cfg.get("token")
        
        if not all([instance_id, token]):
            self.log_action("ZAPI_CONFIG_MISSING", level="warning")
            return False
            
        url = f"https://api.z-api.io/instances/{instance_id}/token/{token}/send-text"
        payload = {"phone": number, "message": text}
        
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code in (200, 201):
            self.log_action("WHATSAPP_SENT_ZAPI", target=number)
            return True
        else:
            self.log_action("WHATSAPP_FAILED_ZAPI", status=response.status_code, response=response.text[:100])
            return False

    def run_cycle(self, **kwargs) -> WorkerResult:
        """
        Ciclo periódico do NotificationWorker.
        """
        enabled = self.notif_config.get("enabled", False)
        provider = self.notif_config.get("provider", "unknown")
        
        metadata = {
            "whatsapp_enabled": enabled,
            "provider": provider,
            "target": self.notif_config.get("target_number"),
            "ntfy_channel": "radio_tjrn"
        }
        
        score = 2 if enabled else 1
        status = "success"
        
        self.log_action("HEARTBEAT", **metadata)
        
        return WorkerResult(status=status, score=score, metadata=metadata)
