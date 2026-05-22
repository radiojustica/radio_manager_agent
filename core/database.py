import os
import sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Resolução de caminho de banco de dados robusto no drive D (produção) com fallback local
DATA_DIR = Path(r"D:\RADIO")
try:
    # Tenta verificar escrita no drive D:
    if not DATA_DIR.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    test_file = DATA_DIR / ".write_test"
    with open(test_file, "w") as f:
        f.write("test")
    os.remove(test_file)
except Exception:
    if getattr(sys, 'frozen', False):
        DATA_DIR = Path(os.path.dirname(sys.executable))
    else:
        DATA_DIR = Path(__file__).resolve().parent.parent

DB_PATH = DATA_DIR / "radio_omni.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# Para SQLite, 'check_same_thread': False é necessário ao rodar as threads do FastAPI
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Garante que as tabelas e colunas existam."""
    Base.metadata.create_all(bind=engine)
    
    import sqlite3
    # Whitelist explícita — nunca interpolar input externo em DDL
    ALLOWED_COLUMNS = {
        "mood": "TEXT",
        "bpm": "INTEGER",
        "valence": "REAL",
        "danceability": "REAL",
        "quarantine_reason": "TEXT",
    }
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    for nome_col, tipo_col in ALLOWED_COLUMNS.items():
        try:
            cursor.execute(f"ALTER TABLE musicas ADD COLUMN {nome_col} {tipo_col}")
        except sqlite3.OperationalError:
            pass  # Coluna já existe — comportamento esperado
    conn.commit()
    conn.close()




