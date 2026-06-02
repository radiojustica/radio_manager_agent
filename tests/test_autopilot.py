import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.database import Base
from core.models import SystemConfig, AutopilotLog
from services.autopilot_service import autopilot_service
from fastapi.testclient import TestClient
from api.manager import app

# Configuração de banco de dados SQLite em memória para testes isolados
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

def test_autopilot_default_state(db_session):
    """Testa se o piloto automático está ativado por padrão."""
    active = autopilot_service.is_autopilot_active(db_session)
    assert active is True

def test_autopilot_toggle(db_session):
    """Testa alternar o estado do piloto automático."""
    # Desativa
    autopilot_service.set_autopilot_active(db_session, False)
    assert autopilot_service.is_autopilot_active(db_session) is False

    # Re-ativa
    autopilot_service.set_autopilot_active(db_session, True)
    assert autopilot_service.is_autopilot_active(db_session) is True

def test_autopilot_logging(db_session):
    """Testa a criação e recuperação de logs de ações corretivas."""
    autopilot_service.log_action(db_session, "PROCESS_RESTART", "ZaraRadio foi reiniciado com sucesso.", success=True)
    autopilot_service.log_action(db_session, "SILENCE_RECOVERY", "Comando PLAY falhou.", success=False)

    logs = autopilot_service.get_logs(db_session)
    assert len(logs) == 2
    assert logs[0].action_type == "SILENCE_RECOVERY"
    assert logs[0].success is False
    assert logs[1].action_type == "PROCESS_RESTART"
    assert logs[1].success is True

def test_autopilot_api_endpoints():
    """Testa os endpoints HTTP do Autopilot usando TestClient."""
    client = TestClient(app)
    
    # 1. GET /api/autopilot/status
    response = client.get("/api/autopilot/status")
    assert response.status_code == 200
    data = response.json()
    assert "active" in data
    assert "stats" in data
    assert "recent_actions" in data

    # 2. POST /api/autopilot/toggle (Desativar)
    response = client.post("/api/autopilot/toggle", json={"active": False})
    assert response.status_code == 200
    assert response.json()["active"] is False

    # 3. GET status novamente para verificar persistência
    response = client.get("/api/autopilot/status")
    assert response.status_code == 200
    assert response.json()["active"] is False

    # 4. POST /api/autopilot/toggle (Ativar)
    response = client.post("/api/autopilot/toggle", json={"active": True})
    assert response.status_code == 200
    assert response.json()["active"] is True
