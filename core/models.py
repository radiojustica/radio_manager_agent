from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float
from core.database import Base
from datetime import datetime

class Musica(Base):
    __tablename__ = "musicas"

    id = Column(Integer, primary_key=True, index=True)
    caminho = Column(String, unique=True, index=True, nullable=False)
    artista = Column(String, default="VARIOUS", index=True)
    titulo = Column(String, nullable=False)
    estilo = Column(String, default="outros", index=True)
    energia = Column(Integer, default=3)
    duracao = Column(Integer, default=210) # Duração em segundos
    bpm = Column(Integer, nullable=True)
    valence = Column(Float, nullable=True)
    danceability = Column(Float, nullable=True)
    
    # Flags de Curadoria
    auditado_acustica = Column(Boolean, default=False)
    redflag = Column(Boolean, default=False)
    mood = Column(String, nullable=True, index=True) # Ex: Ensolarado, Sombrio, Foco
    tema_especial = Column(String, nullable=True, index=True) # Ex: junho, natal, nordestino

    
    # Anti-repetição (Lógica Musical)
    ultima_reproducao = Column(DateTime, nullable=True)
    vezes_tocada = Column(Integer, default=0, index=True)
    
    # Insights da IA
    ai_insight = Column(String, nullable=True)
    quarantine_reason = Column(String, nullable=True)

    def to_dict(self):
        d = {}
        for c in self.__table__.columns:
            val = getattr(self, c.name)
            if isinstance(val, (datetime,)):
                val = val.isoformat() if val else None
            d[c.name] = val
        return d

class RegraProgramacao(Base):
    __tablename__ = "regras_programacao"
    id = Column(Integer, primary_key=True)
    bloco = Column(String, unique=True, nullable=False) # Madrugada, Manha, Tarde, Noite
    hora_inicio = Column(Integer)
    hora_fim = Column(Integer)
    energia_alvo = Column(Integer, default=3)

class SystemConfig(Base):
    __tablename__ = "system_configs"
    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, index=True, nullable=False)
    value = Column(String, nullable=True)

class AutopilotLog(Base):
    __tablename__ = "autopilot_logs"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    action_type = Column(String, nullable=False, index=True) # Ex: PROCESS_RESTART, SILENCE_RECOVERY, OS_PREVENTION
    message = Column(String, nullable=False)
    success = Column(Boolean, default=True)


