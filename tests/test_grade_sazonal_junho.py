# tests/test_grade_sazonal_junho.py
import sys
import os
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

# Adiciona o diretório raiz ao sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.database import Base
from core.models import Musica
from director.grade_rules import GestorFila, montar_bloco
from director.playlist_engine import PlaylistEngine

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

def test_gestor_fila_separacao_junina(temp_db):
    # Insere músicas de teste
    musicas = [
        # Música comum
        Musica(caminho=r"D:\RADIO\MUSICAS\MPB\caetano.mp3", artista="Caetano", titulo="Sampa", estilo="mpb", tema_especial=None, vezes_tocada=0),
        # Junina na pasta física
        Musica(caminho=r"D:\RADIO\MUSICAS\ESPECIAL_JUNHO\luiz.mp3", artista="Luiz Gonzaga", titulo="Olha Pro Céu", estilo="forró", tema_especial="junho", vezes_tocada=0),
        # Junina no acervo geral (pelo estilo forró)
        Musica(caminho=r"D:\RADIO\MUSICAS\REGIONAL\dominguinhos.mp3", artista="Dominguinhos", titulo="Lamento Sertanejo", estilo="forró", tema_especial=None, vezes_tocada=0),
        # Regional nordestina comum
        Musica(caminho=r"D:\RADIO\MUSICAS\REGIONAL\vital.mp3", artista="Vital Farias", titulo="Caso de Amor", estilo="regional", tema_especial=None, vezes_tocada=0),
    ]
    for m in musicas:
        temp_db.add(m)
    temp_db.commit()

    # 1. Testar em Junho (mês 6)
    with patch("director.grade_rules.now_local") as mock_now:
        mock_now.return_value = datetime(2026, 6, 15, 12, 0, 0)
        
        db_musicas = temp_db.query(Musica).all()
        gestor = GestorFila(db_musicas)
        
        # O pool_junino deve conter a música de luiz e de dominguinhos (detectadas dinamicamente)
        assert len(gestor.pool_junino) == 2
        caminhos_juninos = [m.caminho for m in gestor.pool_junino]
        assert r"D:\RADIO\MUSICAS\ESPECIAL_JUNHO\luiz.mp3" in caminhos_juninos
        assert r"D:\RADIO\MUSICAS\REGIONAL\dominguinhos.mp3" in caminhos_juninos
        
        # O pool_geral deve conter Sampa
        assert len(gestor.pool_geral) == 1
        assert gestor.pool_geral[0].titulo == "Sampa"

    # 2. Testar fora de Junho (ex: Maio, mês 5)
    with patch("director.grade_rules.now_local") as mock_now:
        mock_now.return_value = datetime(2026, 5, 15, 12, 0, 0)
        
        db_musicas = temp_db.query(Musica).all()
        gestor = GestorFila(db_musicas)
        
        # Fora de Junho, o pool_junino deve ser vazio (não ativa a sazonalidade de São João)
        assert len(gestor.pool_junino) == 0
        
        # A música de Luiz Gonzaga fica retida (ou excluída) e as outras entram nos pools normais
        assert len(gestor.pool_geral) >= 1

def test_montar_bloco_distribuicao_junina(temp_db):
    # Insere músicas de teste suficientes
    musicas = []
    # 15 Músicas juninas
    for i in range(15):
        musicas.append(Musica(
            caminho=f"D:\\RADIO\\MUSICAS\\ESPECIAL_JUNHO\\forro_{i}.mp3",
            artista=f"Artista Junino {i}",
            titulo=f"Xote {i}",
            estilo="forró",
            tema_especial="junho",
            vezes_tocada=0
        ))
    # 20 Músicas comuns
    for i in range(20):
        musicas.append(Musica(
            caminho=f"D:\\RADIO\\MUSICAS\\MPB\\musica_{i}.mp3",
            artista=f"Artista Comum {i}",
            titulo=f"MPB {i}",
            estilo="mpb",
            tema_especial=None,
            vezes_tocada=0
        ))
    for m in musicas:
        temp_db.add(m)
    temp_db.commit()

    assets = {"vinhetas": [], "spots": [], "boletins": []}

    # Caso 1: Bloco 12H em Junho (100% Junino)
    with patch("director.grade_rules.now_local") as mock_now:
        mock_now.return_value = datetime(2026, 6, 15, 12, 0, 0)
        
        db_musicas = temp_db.query(Musica).all()
        # O acervo em Junho contém os estilos juninos
        playlist = montar_bloco(db_musicas, duracao_alvo_s=600, assets=assets, hora_inicio=12)
        
        # Remove a linha EXTM3U
        playlist_tracks = [p for p in playlist if p.startswith("D:\\")]
        
        # Como o bloco é 100% junino, todas as faixas tocadas devem ser juninas
        for track in playlist_tracks:
            assert "ESPECIAL_JUNHO" in track

    # Caso 2: Bloco 10H em Junho (Misto - 1 junina a cada 3 músicas)
    with patch("director.grade_rules.now_local") as mock_now:
        mock_now.return_value = datetime(2026, 6, 15, 10, 0, 0)
        
        db_musicas = temp_db.query(Musica).all()
        playlist = montar_bloco(db_musicas, duracao_alvo_s=1600, assets=assets, hora_inicio=10)
        
        playlist_tracks = [p for p in playlist if p.startswith("D:\\")]
        
        # Deve ter músicas juninas e comuns na proporção misturada
        juninas = [t for t in playlist_tracks if "ESPECIAL_JUNHO" in t]
        comuns = [t for t in playlist_tracks if "MPB" in t]
        
        assert len(juninas) > 0
        assert len(comuns) > 0
        
        # Verifica a regra de 1 junina a cada 3
        # As posições (0-indexadas) múltiplas de 3 (3, 6, etc.) devem ser do pool junino
        for idx, track in enumerate(playlist_tracks):
            if idx > 0 and idx % 3 == 0:
                assert "ESPECIAL_JUNHO" in track

    # Caso 3: Bloco 20H em Junho (Madrugada/Noite - Padrão normal)
    with patch("director.grade_rules.now_local") as mock_now:
        mock_now.return_value = datetime(2026, 6, 15, 20, 0, 0)
        
        db_musicas = temp_db.query(Musica).all()
        playlist = montar_bloco(db_musicas, duracao_alvo_s=1200, assets=assets, hora_inicio=20)
        
        playlist_tracks = [p for p in playlist if p.startswith("D:\\")]
        
        # Não deve puxar músicas juninas (pois no GestorFila em Junho elas vão para o pool_junino, 
        # e o bloco de 20H busca apenas no pool_geral/pool_regional)
        for track in playlist_tracks:
            assert "ESPECIAL_JUNHO" not in track
