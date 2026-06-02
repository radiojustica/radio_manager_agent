import os
import sqlite3
import json
import pytest
import shutil
from unittest.mock import patch, MagicMock

# Importa as funcoes a serem testadas
# Precisamos adicionar o diretorio 'scripts' ao path se necessario, ou importar diretamente
import sys
scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

from deep_curator import sanitize_filename, collect_pending_songs, apply_decisions

def test_sanitize_filename():
    assert sanitize_filename("Artista/Banda") == "ArtistaBanda"
    assert sanitize_filename("Música: Especial") == "Música Especial"
    assert sanitize_filename('João "Cantor" & Banda') == "João Cantor & Banda"
    assert sanitize_filename("Valores < Proibidos > |") == "Valores Proibidos"
    assert sanitize_filename("  Espaços   Duplos  ") == "Espaços Duplos"
    assert sanitize_filename("") == "UNKNOWN"

@pytest.fixture
def temp_db_and_files(tmp_path):
    # Cria estrutura de pastas simulada
    musicas_dir = tmp_path / "RADIO" / "MUSICAS"
    especial_dir = musicas_dir / "ESPECIAL_JUNHO"
    quarentena_dir = tmp_path / "RADIO" / "QUARENTENA_TJ"
    
    especial_dir.mkdir(parents=True)
    quarentena_dir.mkdir(parents=True)
    
    # Cria arquivos de musica falsos
    song1_path = especial_dir / "musica1.mp3"
    song2_path = especial_dir / "musica2.mp3"
    song1_path.write_text("audio content 1")
    song2_path.write_text("audio content 2")
    
    # Cria banco de dados SQLite temporario
    db_path = tmp_path / "radio_omni.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Cria tabela de musicas
    cursor.execute("""
        CREATE TABLE musicas (
            id INTEGER PRIMARY KEY,
            caminho VARCHAR,
            artista VARCHAR,
            titulo VARCHAR,
            estilo VARCHAR,
            energia INTEGER,
            duracao INTEGER,
            bpm INTEGER,
            valence FLOAT,
            danceability FLOAT,
            auditado_acustica BOOLEAN,
            redflag BOOLEAN,
            mood VARCHAR,
            vezes_tocada INTEGER,
            ai_insight VARCHAR,
            quarantine_reason VARCHAR,
            tema_especial TEXT
        )
    """)
    
    # Insere registros de teste
    cursor.execute("""
        INSERT INTO musicas (caminho, artista, titulo, estilo, energia, duracao, auditado_acustica, redflag, tema_especial)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (str(song1_path), "ARTISTA_A", "musica1", "forró", 3, 180, 0, 0, "junho"))
    
    cursor.execute("""
        INSERT INTO musicas (caminho, artista, titulo, estilo, energia, duracao, auditado_acustica, redflag, tema_especial)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (str(song2_path), "ARTISTA_B", "musica2", "forró", 4, 200, 0, 0, "junho"))
    
    conn.commit()
    conn.close()
    
    return {
        "db_path": str(db_path),
        "quarentena_dir": str(quarentena_dir),
        "song1_path": str(song1_path),
        "song2_path": str(song2_path),
        "especial_dir": str(especial_dir),
        "tmp_path": tmp_path
    }

def test_apply_decisions_approved(temp_db_and_files):
    db_path = temp_db_and_files["db_path"]
    quarentena_dir = temp_db_and_files["quarentena_dir"]
    song1_path = temp_db_and_files["song1_path"]
    especial_dir = temp_db_and_files["especial_dir"]
    
    # Cria decisoes simuladas
    decisions = [
        {
            "id": 1,
            "caminho_original": song1_path,
            "status": "APROVADO",
            "motivo": "Música sem termos inadequados",
            "artista_correto": "Artista A Correto",
            "titulo_correto": "Música 1 Correta",
            "estilo_correto": "forró",
            "tema_especial": "junho"
        }
    ]
    
    decisions_file = "curator_decisions.json"
    with open(decisions_file, "w", encoding="utf-8") as f:
        json.dump(decisions, f)
        
    # Executa a aplicacao das decisoes patcheando os caminhos globais
    with patch("deep_curator.DB_PATH", db_path), \
         patch("deep_curator.QUARENTENA_DIR", quarentena_dir), \
         patch("deep_curator.MUSICAS_DIR", str(temp_db_and_files["tmp_path"] / "RADIO" / "MUSICAS")):
        apply_decisions()
        
    # Verifica se o arquivo original foi movido/renomeado
    caminho_esperado = os.path.join(especial_dir, "Artista A Correto - Música 1 Correta.mp3")
    assert os.path.exists(caminho_esperado)
    assert not os.path.exists(song1_path)
    
    # Verifica banco de dados
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT caminho, artista, titulo, auditado_acustica, redflag, ai_insight FROM musicas WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    
    assert row[0] == caminho_esperado
    assert row[1] == "Artista A Correto"
    assert row[2] == "Música 1 Correta"
    assert row[3] == 1 # auditado_acustica
    assert row[4] == 0 # redflag
    assert row[5] == "Música sem termos inadequados" # ai_insight

def test_apply_decisions_rejected(temp_db_and_files):
    db_path = temp_db_and_files["db_path"]
    quarentena_dir = temp_db_and_files["quarentena_dir"]
    song2_path = temp_db_and_files["song2_path"]
    
    # Cria decisoes simuladas
    decisions = [
        {
            "id": 2,
            "caminho_original": song2_path,
            "status": "REPROVADO",
            "motivo": "Palavrão detectado aos 45 segundos",
            "artista_correto": "Artista B",
            "titulo_correto": "Música 2 Proibida",
            "estilo_correto": "forró",
            "tema_especial": "junho"
        }
    ]
    
    decisions_file = "curator_decisions.json"
    with open(decisions_file, "w", encoding="utf-8") as f:
        json.dump(decisions, f)
        
    # Executa a aplicacao das decisoes
    with patch("deep_curator.DB_PATH", db_path), \
         patch("deep_curator.QUARENTENA_DIR", quarentena_dir), \
         patch("deep_curator.MUSICAS_DIR", str(temp_db_and_files["tmp_path"] / "RADIO" / "MUSICAS")):
        apply_decisions()
        
    # Verifica se o arquivo foi movido para a quarentena
    caminho_esperado = os.path.join(quarentena_dir, "Artista B - Música 2 Proibida.mp3")
    assert os.path.exists(caminho_esperado)
    assert not os.path.exists(song2_path)
    
    # Verifica banco de dados
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT caminho, auditado_acustica, redflag, quarantine_reason, ai_insight FROM musicas WHERE id = 2")
    row = cursor.fetchone()
    conn.close()
    
    assert row[0] == caminho_esperado
    assert row[1] == 1 # auditado_acustica
    assert row[2] == 1 # redflag (reprovada)
    assert row[3] == "Palavrão detectado aos 45 segundos" # quarantine_reason
    assert row[4] == "Palavrão detectado aos 45 segundos" # ai_insight
