import requests
import logging

# Placeholder values that indicate the token/chat_id was never configured
_PLACEHOLDER_VALUES = {"YOUR_BOT_TOKEN_HERE", "YOUR_CHAT_ID_HERE", "", None}


class TelegramNotifier:
    def __init__(self, config: dict):
        self.bot_token = config.get("bot_token")
        self.chat_id = config.get("chat_id")
        self.whatsapp_webhook = config.get("whatsapp_webhook") # URL da Evolution API / Z-API
        self.logger = logging.getLogger("RadioManagerAgent.Notifier")

    @property
    def is_telegram_configured(self) -> bool:
        return self.bot_token not in _PLACEHOLDER_VALUES and self.chat_id not in _PLACEHOLDER_VALUES

    @property
    def is_whatsapp_configured(self) -> bool:
        return bool(self.whatsapp_webhook) and self.whatsapp_webhook not in _PLACEHOLDER_VALUES

    def send_message(self, message: str) -> bool:
        """Envia mensagens via Telegram e/ou WhatsApp Webhook."""
        success = False
        
        # 1. Telegram
        if self.is_telegram_configured:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {"chat_id": self.chat_id, "text": message, "parse_mode": "Markdown"}
            try:
                res = requests.post(url, json=payload, timeout=10)
                if res.status_code == 200: success = True
            except Exception as e:
                self.logger.error(f"Erro Telegram: {e}")

        # 2. WhatsApp (Webhook Local)
        if self.is_whatsapp_configured:
            try:
                # Payload genérico (ajustar conforme API local)
                payload = {"number": self.chat_id, "message": message} 
                res = requests.post(self.whatsapp_webhook, json=payload, timeout=10)
                if res.status_code in [200, 201]: success = True
            except Exception as e:
                self.logger.error(f"Erro WhatsApp Webhook: {e}")

        return success

    def send_alert(self, event_type: str, details: dict) -> bool:
        """Sends a formatted alert message."""
        icons = {
            "START":   "🚀",
            "RESTART": "🔄",
            "ERROR":   "🔴",
            "WARNING": "⚠️",
            "HEALTH":  "📊",
            "LIVE_START": "🎙️",
            "LIVE_END":   "🏁",
        }
        icon = icons.get(event_type, "🔔")
        msg = (
            f"{icon} *RADIO GUARDIAN ALERT*\n\n"
            f"*Type:* {event_type}\n"
            f"*Time:* {details.get('time', 'N/A')}\n"
            f"*Details:* {details.get('message', '')}"
        )
        return self.send_message(msg)


