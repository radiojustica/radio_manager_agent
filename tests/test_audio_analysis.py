import os
import numpy as np
import soundfile as sf
import pytest
from services.curadoria_worker import analisar_acustica_completa

@pytest.fixture
def dummy_audio_file(tmp_path):
    """Gera um arquivo WAV de 40 segundos para teste."""
    path = tmp_path / "test_audio.wav"
    sr = 22050
    duration = 40
    # Gera um tom senoidal simples (440Hz)
    t = np.linspace(0, duration, sr * duration)
    y = 0.5 * np.sin(2 * np.pi * 440 * t)
    
    # Adiciona alguns "beats" para o beat tracker não falhar miseravelmente
    # Vamos colocar um pulso a cada 0.5 segundos (120 BPM)
    pulse_indices = np.arange(0, duration, 0.5) * sr
    for idx in pulse_indices:
        if int(idx) < len(y):
            y[int(idx):int(idx) + 1000] = 0.8
            
    sf.write(str(path), y, sr)
    return str(path)

def test_analisar_acustica_completa(dummy_audio_file):
    """Verifica se a análise retorna as chaves e valores esperados."""
    resultado = analisar_acustica_completa(dummy_audio_file)
    
    # 1. Verificar se as chaves estão presentes
    assert "bpm" in resultado
    assert "valence" in resultado
    assert "danceability" in resultado
    assert "energia" in resultado
    
    # 2. Verificar faixas de valores
    # BPM geralmente é > 0 se detectado, ou 0 em caso de erro
    assert resultado["bpm"] >= 0
    
    # Valence e Danceability devem estar entre 0 e 1 (conforme arredondamento no código)
    assert 0.0 <= resultado["valence"] <= 1.0
    assert 0.0 <= resultado["danceability"] <= 1.0
    
    # Energia deve ser entre 1 e 5
    assert 1 <= resultado["energia"] <= 5

    print(f"\n[TESTE] Resultado da análise: {resultado}")
