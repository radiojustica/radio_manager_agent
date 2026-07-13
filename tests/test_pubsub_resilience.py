# tests/test_pubsub_resilience.py
import os
import sys
import time
import pytest

# Adiciona o diretório raiz do projeto ao sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from services.pubsub_service import PubSubService
from core.reward import RewardStore
import os
import tempfile
import shutil

def test_pubsub_service_in_memory_fallback():
    # Cria uma instância de PubSubService forçando fallback imediato passando porta inexistente
    service = PubSubService(host="localhost", port=9999)
    assert service.use_fallback is True

    received_messages = []
    def callback(msg):
        received_messages.append(msg)

    service.subscribe("teste_fallback", callback)
    
    payload = {"test": "yolo", "value": 42}
    receivers = service.publish("teste_fallback", payload)
    
    # Dá tempo para a thread do callback in-memory executar
    time.sleep(0.2)
    
    assert receivers == 1
    assert len(received_messages) == 1
    assert received_messages[0]["test"] == "yolo"
    assert received_messages[0]["value"] == 42

def test_end_to_end_playlist_publish_and_audit():
    # Teste de integração simulando o ciclo completo:
    # PlaylistWorker gera -> publica em bloco_gerado -> Orquestrador audita -> publica em resultado -> AuditWorker pontua no RewardStore
    temp_dir = tempfile.mkdtemp()
    reward_path = os.path.join(temp_dir, "test_rewards.json")
    
    try:
        reward_store = RewardStore(reward_path)
        service = PubSubService(host="localhost", port=9999) # Força fallback
        
        # Cria arquivos M3U fictício para teste
        m3u_file = os.path.join(temp_dir, "PROG_10H.m3u")
        with open(m3u_file, "w", encoding="cp1252") as f:
            f.write("#EXTM3U\n")
            # Adiciona apenas uma música para simular playlist
            f.write(r"D:\RADIO\MUSICAS\NACIONAL\Leny Andrade.mp3" + "\n")
            
        # Simula Orquestrador que escuta bloco_gerado, executa validação simulada e publica no resultado
        def simulate_orchestrator(msg):
            hora_inicio = msg.get("hora_inicio")
            caminho_m3u = msg.get("caminho_m3u")
            
            # Validação simulada direta
            violations = []
            if "fail" in caminho_m3u:
                violations.append("Duração incorreta")
            status = "success" if not violations else "failed"
            
            service.publish("auditoria:resultado", {
                "hora_inicio": hora_inicio,
                "caminho_m3u": caminho_m3u,
                "status": status,
                "violations": violations,
                "timestamp": "2026-06-16T12:00:00"
            })

        # Simula AuditWorker que escuta resultado e grava no RewardStore
        def simulate_audit_worker(msg):
            status = msg.get("status")
            violations = msg.get("violations", [])
            hora_inicio = msg.get("hora_inicio")
            score = 15 if status == "success" else -10
            
            reward_store.record(
                worker_name="PlaylistWorker",
                score=score,
                violations=violations,
                metadata={"hora_inicio": hora_inicio, "async_audit": True}
            )

        # Inscreve listeners
        service.subscribe("auditoria:bloco_gerado", simulate_orchestrator)
        service.subscribe("auditoria:resultado", simulate_audit_worker)
        
        # Passo 1: PlaylistWorker publica evento de sucesso
        service.publish("auditoria:bloco_gerado", {
            "hora_inicio": 10,
            "caminho_m3u": m3u_file,
            "mood": "Ensolarado",
            "timestamp": "2026-06-16T12:00:00",
            "status": "success"
        })
        
        time.sleep(0.3) # Aguarda execução das threads de PubSub
        
        # Verifica se o score foi gravado no RewardStore
        history = reward_store.history()
        assert len(history) == 1
        assert history[0]["worker"] == "PlaylistWorker"
        assert history[0]["score"] == 15
        assert history[0]["metadata"]["async_audit"] is True

        # Passo 2: PlaylistWorker publica evento de falha simulada
        service.publish("auditoria:bloco_gerado", {
            "hora_inicio": 12,
            "caminho_m3u": "fail_playlist.m3u",
            "mood": "Foco",
            "timestamp": "2026-06-16T12:00:00",
            "status": "success"
        })

        time.sleep(0.3)
        
        history = reward_store.history()
        assert len(history) == 2
        assert history[1]["score"] == -10
        assert history[1]["violations"] == ["Duração incorreta"]
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
