import requests
import logging
import os

logger = logging.getLogger("OmniCore.NotificationService")

def send_whatsapp_alert(message: str):
    """
    Envia um alerta de WhatsApp via CallMeBot API usando a biblioteca requests.
    Implementa um MUTE SAFETY SWITCH via arquivo 'mute_whatsapp.lock'.
    """
    lock_file = os.path.join(os.getcwd(), "mute_whatsapp.lock")
    if os.path.exists(lock_file):
        # Log minimalista para não inundar o arquivo de log também
        return

    url = "https://api.callmebot.com/whatsapp.php"
    params = {
        "phone": "558496066876",
        "apikey": "8552672",
        "text": message
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            logger.info(f"Alerta WhatsApp enviado com sucesso: {message[:50]}...")
        else:
            logger.error(f"Falha ao enviar alerta WhatsApp. Status: {response.status_code}, Resposta: {response.text}")
    except Exception as e:
        logger.error(f"Erro ao conectar com a API do CallMeBot (requests): {e}")

# Mantendo compatibilidade se necessário, mas focando no pedido atual
async def send_whatsapp_notification(message: str):
    # Wrapper síncrono para a nova função, já que o worker manager roda em threads
    send_whatsapp_alert(message)
