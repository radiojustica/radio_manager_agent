from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

SQLALCHEMY_DATABASE_URL = "sqlite:///./core/radio_omni.db"

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
    conn = sqlite3.connect("./core/radio_omni.db")
    cursor = conn.cursor()
    for nome_col, tipo_col in ALLOWED_COLUMNS.items():
        try:
            cursor.execute(f"ALTER TABLE musicas ADD COLUMN {nome_col} {tipo_col}")
        except sqlite3.OperationalError:
            pass  # Coluna já existe — comportamento esperado
    conn.commit()
    conn.close()



