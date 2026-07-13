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

def test_sazonalidade_dia_do_rock(temp_db):
    from director.grade_rules import montar_bloco, GestorFila
    
    # Inserir dados de teste:
    musicas = []
    # 10 de Rock
    for i in range(10):
        musicas.append(Musica(
            caminho=f"D:\\RADIO\\MUSICAS\\ROCK\\rock_track_{i}.mp3",
            artista=f"Rock Band {i}",
            titulo=f"Rock Song {i}",
            estilo="rock",
            energia=4,
            vezes_tocada=0
        ))
    # 10 Gerais (outros estilos)
    for i in range(10):
        musicas.append(Musica(
            caminho=f"D:\\RADIO\\MUSICAS\\MPB\\mpb_track_{i}.mp3",
            artista=f"Artista MPB {i}",
            titulo=f"MPB Song {i}",
            estilo="mpb",
            energia=3,
            vezes_tocada=0
        ))
        
    for m in musicas:
        temp_db.add(m)
    temp_db.commit()
    
    data_bloco = datetime(2026, 7, 13, 10, 0, 0)
    
    # Cria o GestorFila passando a data do bloco (13 de Julho)
    gestor = GestorFila(musicas, data_bloco=data_bloco)
    
    # Testa se o pool_rock foi populado
    assert len(gestor.pool_rock) == 10
    
    # Mock do now_local do grade_rules para retornar o Dia Mundial do Rock
    from unittest.mock import patch
    with patch("director.grade_rules.now_local") as mock_now:
        mock_now.return_value = datetime(2026, 7, 13, 10, 0, 0)
        
        assets = {"vinhetas": [], "spots": [], "boletins": []}
        bloco = montar_bloco(musicas, duracao_alvo_s=3600, assets=assets, hora_inicio=10)
        
        rock_count = 0
        total_musicas = 0
        for item in bloco:
            if item.startswith("#") or "SPOT" in item or "VINHETA" in item or "BOLETIM" in item: 
                continue
            total_musicas += 1
            if "rock" in item.lower():
                rock_count += 1
                
        assert total_musicas > 0
        pct_rock = rock_count / total_musicas
        assert pct_rock >= 0.55


def test_sazonalidade_outras_datas_tematicas(temp_db):
    import tempfile
    import os
    from director.grade_rules import montar_bloco, GestorFila
    from core.compliance_validator import compliance_validator_instance
    
    # Mock das restrições para evitar que o acervo pequeno de teste acuse erro de repetição
    original_constraints = compliance_validator_instance.constraints
    compliance_validator_instance.constraints = {
        "track_separation_count": 2,
        "artist_separation_count": 2
    }
    
    try:
        # 1. Inserir dados de teste:
        musicas = []
        # Músicas de Samba
        for i in range(10):
            musicas.append(Musica(
                caminho=f"D:\\RADIO\\MUSICAS\\SAMBA\\samba_track_{i}.mp3",
                artista=f"Samba Band {i}",
                titulo=f"Samba Song {i}",
                estilo="samba",
                energia=3,
                vezes_tocada=0
            ))
        # Músicas de Choro
        for i in range(10):
            musicas.append(Musica(
                caminho=f"D:\\RADIO\\MUSICAS\\CHORO\\choro_track_{i}.mp3",
                artista=f"Choro Band {i}",
                titulo=f"Choro Song {i}",
                estilo="choro",
                energia=2,
                vezes_tocada=0
            ))
        # Músicas Gerais (MPB)
        for i in range(10):
            musicas.append(Musica(
                caminho=f"D:\\RADIO\\MUSICAS\\MPB\\mpb_track_{i}.mp3",
                artista=f"Artista MPB {i}",
                titulo=f"MPB Song {i}",
                estilo="mpb",
                energia=3,
                vezes_tocada=0
            ))
            
        for m in musicas:
            temp_db.add(m)
        temp_db.commit()
        
        # CASO A: Dia Nacional do Samba (02/12)
        data_bloco_samba = datetime(2026, 12, 2, 10, 0, 0)
        gestor_samba = GestorFila(musicas, data_bloco=data_bloco_samba)
        assert gestor_samba.tema_ativo == "samba"
        assert len(gestor_samba.pool_tema) == 10  # 10 faixas de samba encontradas
        
        assets = {"vinhetas": [], "spots": [], "boletins": []}
        
        # Rodamos montar_bloco mockando a data
        from unittest.mock import patch
        with patch("director.grade_rules.now_local") as mock_now:
            mock_now.return_value = datetime(2026, 12, 2, 10, 0, 0)
            
            bloco_samba = montar_bloco(musicas, duracao_alvo_s=3600, assets=assets, hora_inicio=10)
            
            samba_count = 0
            total_musicas = 0
            for item in bloco_samba:
                if item.startswith("#") or "SPOT" in item or "VINHETA" in item or "BOLETIM" in item: 
                    continue
                total_musicas += 1
                if "samba" in item.lower():
                    samba_count += 1
                    
            assert total_musicas > 0
            pct_samba = samba_count / total_musicas
            # Cota de 50% de Samba (mínimo de 45% exigido no validador)
            assert pct_samba >= 0.45
            
            # Validar via Compliance usando arquivo temporário
            with tempfile.NamedTemporaryFile(delete=False, suffix=".m3u", mode="w", encoding="cp1252") as tmp:
                tmp.write("\n".join(bloco_samba))
                tmp_path = tmp.name
            
            try:
                # Mock do SessionLocal interno do compliance_validator para ler do banco em memória
                with patch("core.compliance_validator.SessionLocal") as mock_session:
                    mock_session.return_value = temp_db
                    violations = compliance_validator_instance.validate_playlist(tmp_path, hour=10, date_context=data_bloco_samba)
                    theme_violations = [v for v in violations if "tema" in v or "samba" in v]
                    assert len(theme_violations) == 0
            finally:
                try:
                    os.unlink(tmp_path)
                except:
                    pass

        # CASO B: Dia Nacional do Choro (23/04)
        data_bloco_choro = datetime(2026, 4, 23, 10, 0, 0)
        gestor_choro = GestorFila(musicas, data_bloco=data_bloco_choro)
        assert gestor_choro.tema_ativo == "choro"
        assert len(gestor_choro.pool_tema) == 10
        
        with patch("director.grade_rules.now_local") as mock_now:
            mock_now.return_value = datetime(2026, 4, 23, 10, 0, 0)
            
            bloco_choro = montar_bloco(musicas, duracao_alvo_s=3600, assets=assets, hora_inicio=10)
            
            choro_count = 0
            total_musicas = 0
            for item in bloco_choro:
                if item.startswith("#") or "SPOT" in item or "VINHETA" in item or "BOLETIM" in item: 
                    continue
                total_musicas += 1
                if "choro" in item.lower():
                    choro_count += 1
                    
            assert total_musicas > 0
            pct_choro = choro_count / total_musicas
            assert pct_choro >= 0.45
            
            # Validar via Compliance usando arquivo temporário
            with tempfile.NamedTemporaryFile(delete=False, suffix=".m3u", mode="w", encoding="cp1252") as tmp:
                tmp.write("\n".join(bloco_choro))
                tmp_path = tmp.name
                
            try:
                with patch("core.compliance_validator.SessionLocal") as mock_session:
                    mock_session.return_value = temp_db
                    violations = compliance_validator_instance.validate_playlist(tmp_path, hour=10, date_context=data_bloco_choro)
                    theme_violations = [v for v in violations if "tema" in v or "choro" in v]
                    assert len(theme_violations) == 0
            finally:
                try:
                    os.unlink(tmp_path)
                except:
                    pass
    finally:
        compliance_validator_instance.constraints = original_constraints

