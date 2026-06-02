import logging
import os
import urllib.parse
import requests
from typing import Dict

logger = logging.getLogger("OmniCore.WhatsAppNotifier")

class WhatsAppNotifier:
    """Notifier que envia mensagens via CallMeBot (WhatsApp).

    A configuração esperada vem de ``settings.json`` em ``notifications.whatsapp`` e
    deve conter, ao menos, ``url``, ``apikey`` e ``target_number``. Se algum campo
    estiver ausente, a notificação será apenas registrada nos logs.
    """

    def __init__(self, config: Dict):
        self.enabled = False
        # Normaliza o dicionário: pode vir direto do JSON ou com variáveis de ambiente já interpoladas.
        self.url = config.get("url") or config.get("evolution", {}).get("url")
        self.apikey = config.get("apikey") or config.get("evolution", {}).get("apikey")
        self.target_number = config.get("target_number") or config.get("target_number")
        if not self.url or not self.apikey or not self.target_number:
            logger.warning(
                "Configuração do WhatsApp incompleta (url/apikey/target_number). Notificações serão simuladas."
            )
        else:
            self.enabled = True
            logger.info("WhatsAppNotifier configurado para enviar via CallMeBot.")

    def send_alert(self, tipo: str, payload: Dict):
        """Envia um alerta formatado.

        ``tipo`` – identificador da mensagem (ex.: ``PLAYLIST_GENERATED``).
        ``payload`` – dicionário serializável com os dados da notificação.
        """
        try:
            message = f"[{tipo}] {payload}"
            if self.enabled:
                # CallMeBot espera parâmetros via query‑string
                params = {
                    "phone": self.target_number,
                    "text": message,
                    "apikey": self.apikey,
                }
                # Alguns servidores exigem que o texto seja URL‑encoded
                encoded_params = urllib.parse.urlencode(params, safe="")
                request_url = f"{self.url}?{encoded_params}"
                resp = requests.get(request_url, timeout=5)
                if resp.status_code == 200:
                    logger.info(f"WhatsApp enviado: {message}")
                else:
                    logger.error(
                        f"Falha ao enviar WhatsApp ({resp.status_code}): {resp.text}"
                    )
            else:
                logger.info(f"[SIMULADO] WhatsApp: {message}")
        except Exception as e:
            logger.exception(f"Erro no WhatsAppNotifier.send_alert: {e}")
