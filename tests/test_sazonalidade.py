import sys
from pathlib import Path
from datetime import datetime

# Adiciona o diretório raiz ao sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.database import Base
from core.models import Musica
from director.playlist_engine import PlaylistEngine

# Setup de banco de dados em memória para teste isolado
@pytest.fixture
def temp_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()

def test_filtro_sazonalidade_caminho_e_tag(temp_db):
    # Inserir dados de teste
    musicas = [
        # Música de natal na pasta física, sem tag (simulando vazamento anterior)
        Musica(
            caminho=r"D:\RADIO\MUSICAS\ESPECIAL_NATAL\01_noite_feliz.mp3",
            artista="Artistas Natalinos",
            titulo="Noite Feliz",
            estilo="pop",
            tema_especial=None,
            vezes_tocada=0
        ),
        # Música de junho na pasta física, sem tag
        Musica(
            caminho=r"D:\RADIO\MUSICAS\ESPECIAL_JUNHO\02_olha_pro_ceu.mp3",
            artista="Luiz Gonzaga",
            titulo="Olha Pro Céu",
            estilo="forro",
            tema_especial=None,
            vezes_tocada=0
        ),
        # Música normal
        Musica(
            caminho=r"D:\RADIO\MUSICAS\MPB\caetano_veloso.mp3",
            artista="Caetano Veloso",
            titulo="Sampa",
            estilo="mpb",
            tema_especial=None,
            vezes_tocada=0
        ),
        # Música com tag explícita de natal (fora da pasta especial)
        Musica(
            caminho=r"D:\RADIO\MUSICAS\MPB\jingle_bells_jazz.mp3",
            artista="Various",
            titulo="Jingle Bells Jazz",
            estilo="jazz",
            tema_especial="natal",
            vezes_tocada=0
        ),
        # Música com tag explícita de junho
        Musica(
            caminho=r"D:\RADIO\MUSICAS\MPB\sao_joao_diferente.mp3",
            artista="Various",
            titulo="São João Diferente",
            estilo="forro",
            tema_especial="junho",
            vezes_tocada=0
        )
    ]
    for m in musicas:
        temp_db.add(m)
    temp_db.commit()

    # Vamos mockar o now_local do playlist_engine para retornar datas específicas
    from unittest.mock import patch
    
    # CASO 1: Testar em Maio (Mês 5 - Não é época de natal nem junho)
    with patch("director.playlist_engine.now_local") as mock_now:
        mock_now.return_value = datetime(2026, 5, 26, 12, 0, 0)
        
        # Estilos consultados
        estilos = ["pop", "forro", "mpb", "jazz"]
        candidatas = PlaylistEngine._buscar_acervo(temp_db, estilos)
        
        # Somente a música normal (Caetano Veloso - Sampa) deve ser retornada!
        # Todas as outras (natal e junho, tanto por pasta física quanto por tag) devem ser filtradas.
        assert len(candidatas) == 1
        assert candidatas[0].titulo == "Sampa"

    # CASO 2: Testar em Dezembro (Mês 12 - Permite natal, mas não permite junho)
    with patch("director.playlist_engine.now_local") as mock_now:
        mock_now.return_value = datetime(2026, 12, 25, 12, 0, 0)
        
        estilos = ["pop", "forro", "mpb", "jazz"]
        candidatas = PlaylistEngine._buscar_acervo(temp_db, estilos)
        
        # Devem retornar: Noite Feliz (caminho natal), Sampa (normal), Jingle Bells Jazz (tag natal).
        # As músicas de junho (caminho e tag) devem ser bloqueadas.
        assert len(candidatas) == 3
        titulos = {c.titulo for c in candidatas}
        assert "Noite Feliz" in titulos
        assert "Sampa" in titulos
        assert "Jingle Bells Jazz" in titulos
        assert "Olha Pro Céu" not in titulos
        assert "São João Diferente" not in titulos

    # CASO 3: Testar em Junho (Mês 6 - Permite junho, mas não permite natal)
    with patch("director.playlist_engine.now_local") as mock_now:
        mock_now.return_value = datetime(2026, 6, 24, 12, 0, 0)
        
        estilos = ["pop", "forro", "mpb", "jazz"]
        candidatas = PlaylistEngine._buscar_acervo(temp_db, estilos)
        
        # Devem retornar: Olha Pro Céu (caminho junho), Sampa (normal), São João Diferente (tag junho).
        # As músicas de natal (caminho e tag) devem ser bloqueadas.
        assert len(candidatas) == 3
        titulos = {c.titulo for c in candidatas}
        assert "Olha Pro Céu" in titulos
        assert "Sampa" in titulos
        assert "São João Diferente" in titulos
        assert "Noite Feliz" not in titulos
        assert "Jingle Bells Jazz" not in titulos
