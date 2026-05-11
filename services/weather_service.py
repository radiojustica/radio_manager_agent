import logging
from datetime import datetime

logger = logging.getLogger("OmniCore.WeatherService")

def get_natal_weather_mood():
    """
    Motor Local de Sugestão de Mood (Substitui a API Externa de Clima).
    Calcula a 'vibe' da rádio baseado na hora do dia e dia da semana.
    
    Retorna: 'Ensolarado', 'Nublado' ou 'Chuvoso'
    (Sendo 'Ensolarado' mais energético, 'Nublado' médio e 'Chuvoso' mais calmo)
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


