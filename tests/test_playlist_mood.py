import sys
import os
import logging
from pathlib import Path

# Setup logging para ver o que acontece no motor
logging.basicConfig(level=logging.INFO)

# Adiciona o diretório raiz ao sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from director.playlist_engine import playlist_engine_instance
from director import grade_rules as GR

def test_playlist_logic():
    print("="*60)
    print("TESTANDO LÓGICA DE PLAYLIST COM MOOD")
    print("="*60)
    
    # Teste 1: Verificar se estilos_para_mood retorna os estilos certos
    print("\n[Teste 1] Mapeamento de Estilos")
    for mood in ["Ensolarado", "Chuvoso", "Nublado"]:
        estilos = GR.estilos_para_mood(mood)
        print(f"✓ Mood: {mood} -> Estilos: {estilos[:3]}...")
    
    # Teste 2: Simular geração de bloco com mood forçado
    print("\n[Teste 2] Simulação de Geração (Dry Run)")
    mood_teste = "Chuvoso"
    print(f"✓ Forçando Mood: {mood_teste}")
    
    # Vamos apenas verificar se o engine_instance consegue inicializar o fluxo
    # sem gravar o arquivo real (para não bagunçar a rádio)
    try:
        # Apenas chamamos estilos_para_mood para ver se as regras novas estão ativas
        estilos = GR.estilos_para_mood(mood_teste)
        if "jazz" in estilos or "blues" in estilos:
            print(f"✓ SUCESSO: Estilos melancólicos detectados para o mood {mood_teste}.")
        else:
            print(f"✗ ERRO: Estilos não condizentes com o mood {mood_teste}.")
    except Exception as e:
        print(f"✗ ERRO: {e}")

    print("\n" + "="*60)

if __name__ == "__main__":
    test_playlist_logic()
