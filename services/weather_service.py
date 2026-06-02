import logging
import requests
from datetime import datetime
from core.time_utils import now_local

logger = logging.getLogger("OmniCore.WeatherService")

import time

# Coordenadas de Natal/RN (Base de operação)
LATITUDE = -5.79448
LONGITUDE = -35.211

# Cache em memória para evitar rate limit na API de clima
_cached_mood = None
_last_check = 0.0
CACHE_DURATION_SECONDS = 900  # 15 minutos

def get_natal_weather_mood() -> str:
    """
    Consulta a API Open-Meteo para obter o clima real de Natal/RN.
    Mapeia o weathercode para os moods da rádio: Ensolarado, Nublado, Chuvoso.
    Utiliza cache local para não sobrecarregar a API a cada requisição de telemetria.
    """
    global _cached_mood, _last_check
    current_time = time.time()

    if _cached_mood is not None and (current_time - _last_check) < CACHE_DURATION_SECONDS:
        return _cached_mood

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
            
            if weather_code == 0:
                mood = "Ensolarado"
            elif weather_code in [1, 2, 3, 45, 48]:
                mood = "Nublado"
            else:
                mood = "Chuvoso"
            
            _cached_mood = mood
            _last_check = current_time
            return mood

    except Exception as e:
        logger.warning(f"[WeatherService] Falha ao consultar API de clima ({e}). Usando heurística local.")
        # Cacheia o fallback por 60 segundos em caso de falha para evitar spam na API se ela estiver com problemas
        fallback_mood = get_fallback_mood()
        _cached_mood = fallback_mood
        _last_check = current_time - (CACHE_DURATION_SECONDS - 60)
        return fallback_mood
    
    # Se de alguma forma chegar aqui sem retornar
    return get_fallback_mood()

def get_fallback_mood() -> str:
    """
    Heurística local baseada na hora do dia e dia da semana.
    Usada apenas se a API externa falhar.
    """
    now = now_local()
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
