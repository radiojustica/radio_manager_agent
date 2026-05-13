import pytest
import os
from services.curadoria_worker import analisar_acustica_completa, processar_arquivo
from core.database import SessionLocal, init_db
from core.models import Musica

def test_audio_quality_metrics():
    # Teste com um arquivo de áudio real se disponível, ou mockar librosa
    # Aqui vamos focar na lógica de processamento
    init_db()
    db = SessionLocal()
    
    # Criar música fake para teste
    m_fake = Musica(
        caminho="fake_path_noisy.mp3",
        artista="Test",
        titulo="Noisy Track",
        auditado_acustica=False
    )
    db.add(m_fake)
    db.commit()
    m_id = m_fake.id
    
    # Mockar analisar_acustica_completa para retornar baixa qualidade
    import services.curadoria_worker as cw
    original_analise = cw.analisar_acustica_completa
    cw.analisar_acustica_completa = lambda x: {
        "energia": 1, 
        "bpm": 120, 
        "valence": 0.5, 
        "danceability": 0.5, 
        "flatness": 0.6
    }
    
    try:
        # Mockar shutil.move para não mover arquivos reais
        import shutil
        original_move = shutil.move
        shutil.move = lambda x, y: print(f"Mock move: {x} -> {y}")
        
        # Mockar Mutagen e carregar librosa para não falhar no início
        from unittest.mock import MagicMock
        import mutagen
        mutagen.File = MagicMock(return_value=MagicMock(info=MagicMock(length=100)))
        
        import librosa
        librosa.load = MagicMock(return_value=(None, 22050))
        
        res = processar_arquivo(m_id, "fake_path_noisy.mp3")
        
        assert res["status"] == "QUARANTINED"
        assert "Baixa Energia" in res["motivo"] or "Ruído Excessivo" in res["motivo"]
        
        shutil.move = original_move
    finally:
        cw.analisar_acustica_completa = original_analise
        db.delete(m_fake)
        db.commit()
        db.close()

if __name__ == "__main__":
    pytest.main([__file__])
