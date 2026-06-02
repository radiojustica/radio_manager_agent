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
        "tema_especial": "TEXT",
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
    
    # Inicialização da grade padrão na tabela system_configs
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        # Verifica se já existe a chave weekly_schedule
        cursor.execute("SELECT id FROM system_configs WHERE key = 'weekly_schedule'")
        row = cursor.fetchone()
        if not row:
            import json
            # JSON da grade semanal padrão com base nas regras atualizadas do usuário
            grade_padrao = {
                "legendas": {
                    "SPOT": {"tipo": "vinheta", "duracao": "curto", "pasta": "D:\\RADIO\\SPOTS"},
                    "VH_INSTITUCIONAL": {"tipo": "vinheta", "duracao": "curto", "pasta": "D:\\RADIO\\VINHETAS"},
                    "BOLETIM": {"tipo": "boletim", "duracao": "1-2 min", "pasta_raiz": "D:\\SERVIDOR\\BOLETINS"},
                    "PROGRAMAS": {
                        "GIRO_NAS_COMARCAS": {"duracao_minutos": 10, "pasta": "D:\\SERVIDOR\\PROGRAMAS\\PROGRAMA_40\\GIRONASCOMARCAS"},
                        "MEMORIA_DA_JUSTICA": {"duracao_minutos": 40, "pasta": "D:\\SERVIDOR\\PROGRAMAS\\PROGRAMA_40\\MEMORIA"},
                        "LEVEMENTE": {"duracao_minutos": 40, "pasta": "D:\\SERVIDOR\\PROGRAMAS\\PROGRAMA_40\\LEVEMENTE"},
                        "NOTICIAS_DO_JUDICIARIO": {"duracao_minutos": 5, "pasta": "D:\\SERVIDOR\\DRIVE\\RADIO TJRN CONTEÚDO\\NOT JUDICIARIO (5 MIN)"}
                    }
                },
                "grade_diaria": {
                    "madrugada_manha": {
                        "inicio": "00:01",
                        "fim": "08:30",
                        "loop": {"intervalo_minutos": 30, "estrutura": ["SPOT", "BOLETIM", "SPOT"]}
                    },
                    "noite_madrugada": {
                        "inicio": "18:00",
                        "fim": "23:59",
                        "loop": {"intervalo_minutos": 30, "estrutura": ["SPOT", "BOLETIM", "SPOT"]}
                    }
                },
                "excecoes_diurnas": {
                    "segunda": {
                        "09:00": ["SPOT", "BOLETIM", "SPOT", "MUSICA"],
                        "10:00": ["SPOT", "BOLETIM", "SPOT", "MUSICA"],
                        "10:45": ["SPOT", "NOTICIAS_DO_JUDICIARIO", "SPOT", "MUSICA"],
                        "11:30": ["SPOT", "VH_INSTITUCIONAL", "SPOT", "MUSICA"],
                        "12:00": ["SPOT", "BOLETIM", "SPOT", "MUSICA"],
                        "16:00": ["VH_INSTITUCIONAL", "MEMORIA_DA_JUSTICA", "MUSICA"],
                        "17:30": ["NOTICIAS_DO_JUDICIARIO"]
                    },
                    "terca": {
                        "09:00": ["SPOT", "VH_INSTITUCIONAL", "MUSICA"],
                        "10:00": ["SPOT", "VH_INSTITUCIONAL", "MUSICA"],
                        "10:45": ["SPOT", "NOTICIAS_DO_JUDICIARIO", "SPOT", "MUSICA"],
                        "11:30": ["SPOT", "BOLETIM", "SPOT", "MUSICA"],
                        "12:00": ["SPOT", "BOLETIM", "SPOT", "MUSICA"],
                        "15:00": ["SPOT", "BOLETIM", "GIRO_NAS_COMARCAS", "MUSICA"],
                        "17:30": ["NOTICIAS_DO_JUDICIARIO"]
                    },
                    "quarta": {
                        "09:00": ["SPOT", "BOLETIM", "SPOT", "MUSICA"],
                        "10:00": ["SPOT", "BOLETIM", "SPOT", "MUSICA"],
                        "10:45": ["SPOT", "NOTICIAS_DO_JUDICIARIO", "SPOT", "MUSICA"],
                        "11:30": ["SPOT", "BOLETIM", "SPOT", "MUSICA"],
                        "12:00": ["SPOT", "BOLETIM", "SPOT", "MUSICA"],
                        "17:30": ["NOTICIAS_DO_JUDICIARIO"]
                    },
                    "quinta": {
                        "09:00": ["SPOT", "VH_INSTITUCIONAL", "LEVEMENTE", "MUSICA"],
                        "10:00": ["SPOT", "BOLETIM", "SPOT", "MUSICA"],
                        "10:45": ["SPOT", "NOTICIAS_DO_JUDICIARIO", "SPOT", "MUSICA"],
                        "11:30": ["SPOT", "BOLETIM", "SPOT", "MUSICA"],
                        "12:00": ["SPOT", "BOLETIM", "SPOT", "MUSICA"],
                        "17:30": ["NOTICIAS_DO_JUDICIARIO"]
                    },
                    "sexta": {
                        "09:00": ["SPOT", "VH_INSTITUCIONAL", "MUSICA"],
                        "10:00": ["SPOT", "BOLETIM", "SPOT", "MUSICA"],
                        "10:45": ["SPOT", "NOTICIAS_DO_JUDICIARIO", "SPOT", "MUSICA"],
                        "11:30": ["SPOT", "VH_INSTITUCIONAL", "SPOT", "MUSICA"],
                        "12:00": ["SPOT", "VH_INSTITUCIONAL", "MUSICA"],
                        "17:30": ["NOTICIAS_DO_JUDICIARIO"]
                    }
                },
                "final_de_semana": {
                    "sabado": {
                        "06:00_15:00": {"loop": {"intervalo_minutos": 30, "estrutura": ["SPOT", "BOLETIM", "SPOT", "MUSICA"]}},
                        "15:00_18:00": {"loop": {"intervalo_minutos": 30, "estrutura": ["SPOT", "BOLETIM", "SPOT", "MUSICA"]}}
                    },
                    "domingo": {
                        "06:00_15:00": {"loop": {"intervalo_minutos": 30, "estrutura": ["SPOT", "BOLETIM", "SPOT", "MUSICA"]}},
                        "15:00_18:00": {"loop": {"intervalo_minutos": 30, "estrutura": ["SPOT", "BOLETIM", "SPOT", "MUSICA"]}}
                    }
                }
            }
            # Insere a nova chave
            cursor.execute(
                "INSERT INTO system_configs (key, value) VALUES (?, ?)",
                ("weekly_schedule", json.dumps(grade_padrao, indent=4))
            )
            conn.commit()
    except Exception as e:
        import logging
        logging.getLogger("OmniCore.DB").error(f"Erro ao inicializar grade padrao: {e}")
    finally:
        try:
            conn.close()
        except:
            pass




