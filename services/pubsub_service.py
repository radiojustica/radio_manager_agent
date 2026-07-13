# services/pubsub_service.py
"""
Pub/Sub Service — Omni Core V3
==============================
Gerenciador leve de mensagens assíncronas para cooperação entre agentes.
Suporta Redis local com fallback automático para emulação in-memory (Circuit Breaker).
"""

import json
import logging
import threading
import time
from typing import Callable, Any

logger = logging.getLogger("OmniCore.PubSubService")

class InMemoryPubSub:
    """Emulador de Pub/Sub em memória e thread-safe para fallback."""
    def __init__(self):
        self.subscribers: dict[str, list[Callable[[dict], None]]] = {}
        self.lock = threading.Lock()

    def subscribe(self, channel: str, callback: Callable[[dict], None]):
        with self.lock:
            self.subscribers.setdefault(channel, []).append(callback)
            logger.debug(f"[InMemory] Subscrito no canal: {channel}")

    def publish(self, channel: str, message: dict) -> int:
        with self.lock:
            if channel not in self.subscribers:
                return 0
            count = 0
            for cb in self.subscribers[channel]:
                # Executa o callback em uma thread separada para manter assincronismo
                threading.Thread(target=self._safe_execute, args=(cb, message), daemon=True).start()
                count += 1
            return count

    def _safe_execute(self, callback: Callable[[dict], None], message: dict):
        try:
            callback(message)
        except Exception as e:
            logger.error(f"[InMemory] Erro ao executar callback: {e}")


class PubSubService:
    def __init__(self, host: str = "localhost", port: int = 6379):
        self.host = host
        self.port = port
        self.client = None
        self.use_fallback = False
        self.in_memory_bus = InMemoryPubSub()
        self.redis_sub_threads = []
        self._connect()

    def _connect(self):
        """Tenta conectar ao Redis local. Ativa fallback se falhar."""
        try:
            import redis
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                socket_timeout=2.0,
                socket_connect_timeout=2.0,
                decode_responses=True
            )
            # Testa conexão
            self.client.ping()
            logger.info("✓ Conectado ao Redis local com sucesso para Pub/Sub.")
            self.use_fallback = False
        except Exception as e:
            logger.warning(
                f"⚠️ Falha ao conectar ao Redis ({e}). "
                "Ativando fallback em memória (YOLO Mode robusto)."
            )
            self.use_fallback = True
            self.client = None

    def publish(self, channel: str, message: dict) -> int:
        """Publica uma mensagem em um canal."""
        if self.use_fallback or not self.client:
            return self.in_memory_bus.publish(channel, message)

        try:
            payload = json.dumps(message, ensure_ascii=False)
            receivers = self.client.publish(channel, payload)
            logger.info(f"[PubSub] Mensagem publicada no canal '{channel}' (Recebedores: {receivers})")
            return receivers
        except Exception as e:
            logger.error(f"[PubSub] Falha ao publicar no Redis ({e}). Chovendo no molhado: usando fallback...")
            self.use_fallback = True
            return self.in_memory_bus.publish(channel, message)

    def subscribe(self, channel: str, callback: Callable[[dict], None]):
        """Inscreve um callback para escutar um canal assincronamente."""
        if self.use_fallback or not self.client:
            self.in_memory_bus.subscribe(channel, callback)
            return

        # Para o Redis, precisamos de uma thread escutando o canal (PubSub listener)
        def redis_listener():
            try:
                pubsub = self.client.pubsub()
                pubsub.subscribe(channel)
                logger.info(f"[PubSub] Thread listener iniciada para canal Redis: {channel}")
                
                for message in pubsub.listen():
                    if message and message['type'] == 'message':
                        try:
                            data = json.loads(message['data'])
                            callback(data)
                        except Exception as json_err:
                            logger.error(f"[PubSub] Erro ao decodificar JSON do Redis no canal {channel}: {json_err}")
            except Exception as conn_err:
                logger.error(f"[PubSub] Falha na conexão da thread listener do Redis ({conn_err}). Revertendo para emulador.")
                self.use_fallback = True
                self.in_memory_bus.subscribe(channel, callback)

        t = threading.Thread(target=redis_listener, daemon=True)
        t.start()
        self.redis_sub_threads.append(t)

# Instância singleton global do serviço PubSub
pubsub_service_instance = PubSubService()
