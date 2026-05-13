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
    
    # Lógica de migração manual para SQLite (adiciona coluna se não existir)
    import sqlite3
    conn = sqlite3.connect("./core/radio_omni.db")
    cursor = conn.cursor()
    
    colunas = [
        ("mood", "TEXT"),
        ("bpm", "INTEGER"),
        ("valence", "REAL"),
        ("danceability", "REAL"),
        ("quarantine_reason", "TEXT")
    ]
    
    for nome_col, tipo_col in colunas:
        try:
            cursor.execute(f"ALTER TABLE musicas ADD COLUMN {nome_col} {tipo_col}")
            print(f"Coluna '{nome_col}' adicionada com sucesso.")
        except sqlite3.OperationalError:
            # Coluna já existe ou erro operacional (ignorar)
            pass
            
    conn.commit()
    conn.close()



