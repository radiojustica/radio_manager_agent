"""
Notifier simples de mensagens via WhatsApp (stub).
Utiliza um serviço externo (ex.: Twilio) para enviar mensagens.
Nesta implementação, a função send_alert apenas registra o envio.
"""

import logging

class WhatsAppNotifier:
    def __init__(self, config: dict):
        self.config = config
        self.logger = logging.getLogger("RadioManagerAgent.WhatsAppNotifier")
        required = ['account_sid', 'auth_token', 'from_number', 'to_number']
        missing = [k for k in required if k not in self.config]
        if missing:
            self.logger.warning(f"Configuração do WhatsApp incompleta, faltando: {missing}")
        else:
            self.logger.info("WhatsAppNotifier configurado.")

    def send_alert(self, title: str, payload: dict):
        """Envia alerta via WhatsApp.
        * title – tipo de alerta (ex.: 'DAILY_LOG')
        * payload – dicionário contendo 'time' e 'message'
        """
        try:
            msg = payload.get('message', '')
            self.logger.info(f"[WhatsApp] {title}: {msg}")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao enviar mensagem WhatsApp: {e}")
            return False
