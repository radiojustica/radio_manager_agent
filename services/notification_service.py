import httpx
import logging

logger = logging.getLogger(__name__)

async def send_whatsapp_notification(message: str):
    """
    Envia uma notificação de WhatsApp via CallMeBot API.
    """
    url = "https://api.callmebot.com/whatsapp.php"
    params = {
        "phone": "+5584996066876",
        "text": message,
        "apikey": "8552672"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            if response.status_code == 200:
                logger.info(f"Notificação enviada com sucesso: {message}")
            else:
                logger.error(f"Falha ao enviar notificação. Status: {response.status_code}, Response: {response.text}")
    except Exception as e:
        logger.error(f"Erro ao conectar com a API do CallMeBot: {str(e)}")
