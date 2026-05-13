import sys
import os
from pathlib import Path

# Adiciona o diretório raiz ao sys.path para conseguir importar os serviços
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.weather_service import get_natal_weather_mood

def test_weather():
    print("="*60)
    print("TESTANDO SERVIÇO DE CLIMA (OPEN-METEO)")
    print("="*60)
    
    try:
        mood = get_natal_weather_mood()
        print(f"✓ Mood detectado: {mood}")
        if mood in ["Ensolarado", "Nublado", "Chuvoso"]:
            print("✓ SUCESSO: Mood válido retornado.")
        else:
            print("✗ ERRO: Mood inválido retornado.")
    except Exception as e:
        print(f"✗ ERRO FATAL: {e}")
    
    print("="*60)

if __name__ == "__main__":
    test_weather()
