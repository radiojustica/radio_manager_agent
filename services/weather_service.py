import logging
import requests
from datetime import datetime

logger = logging.getLogger("OmniCore.WeatherService")

# Coordenadas de Natal/RN (Base de operação)
LATITUDE = -5.79448
LONGITUDE = -35.211

def get_natal_weather_mood() -> str:
    """
    Consulta a API Open-Meteo para obter o clima real de Natal/RN.
    Mapeia o weathercode para os moods da rádio: Ensolarado, Nublado, Chuvoso.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "current_weather": "true",
        "timezone": "America/Fortaleza"
    }

    try:
        logger.info(f"[WeatherService] Consultando clima real para Natal/RN ({LATITUDE}, {LONGITUDE})...")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if "current_weather" in data:
            weather_code = data["current_weather"].get("weathercode", 0)
            logger.info(f"[WeatherService] WeatherCode recebido: {weather_code}")
            
            # Mapeamento Open-Meteo Weather Codes
            # 0: Céu limpo
            # 1, 2, 3: Parcialmente nublado, nublado
            # 45, 48: Nevoeiro
            # 51, 53, 55: Garoa
            # 61, 63, 65: Chuva
            # 71, 73, 75: Neve
            # 80, 81, 82: Pancadas de chuva
            # 95, 96, 99: Tempestade
            
            if weather_code == 0:
                return "Ensolarado"
            elif weather_code in [1, 2, 3, 45, 48]:
                return "Nublado"
            else:
                return "Chuvoso"

    except Exception as e:
        logger.warning(f"[WeatherService] Falha ao consultar API de clima ({e}). Usando heurística local.")
    
    return get_fallback_mood()

def get_fallback_mood() -> str:
    """
    Heurística local baseada na hora do dia e dia da semana.
    Usada apenas se a API externa falhar.
    """
    now = datetime.now()
    hour = now.hour
    weekday = now.weekday() # 0 = Seg, 6 = Dom
    
    # Finais de semana (Sexta à noite até Domingo)
    if weekday == 4 and hour >= 18:
        return "Ensolarado" # Sextou!
    if weekday in [5, 6]:
        if 8 <= hour <= 19:
            return "Ensolarado" # Fim de semana de dia
        else:
            return "Nublado" # Fim de semana à noite
            
    # Dias de semana
    if 5 <= hour < 9:
        return "Ensolarado" # Manhã animada para acordar
    elif 9 <= hour < 18:
        return "Nublado" # Horário comercial focado
    elif 18 <= hour < 22:
        return "Ensolarado" # Volta para casa / Happy hour
    else:
        return "Chuvoso" # Madrugada tranquila
