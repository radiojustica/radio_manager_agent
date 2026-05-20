import threading
import socket
import logging
import time
from typing import Any
from core.worker_base import WorkerBase, WorkerResult
from core.reward import RewardStore

logger = logging.getLogger("OmniCore.Worker.ApiWorker")

class ApiWorker(WorkerBase):
    def __init__(self, reward_store: RewardStore | None = None, config: dict[str, Any] | None = None):
        super().__init__("ApiWorker", reward_store, config)
        self.host = self.config.get("host", "0.0.0.0")
        self.port = self.config.get("port", 8001)
        self.api_thread = None
        self._server_started = False

    def _is_port_open(self) -> bool:
        """Verifica se a porta da API está aberta."""
        try:
            with socket.create_connection(("127.0.0.1", self.port), timeout=1.0):
                return True
        except (socket.timeout, ConnectionRefusedError):
            return False
        except Exception as e:
            self.log_error(e, "PORT_CHECK_FAILED")
            return False

    def _start_server(self):
        """Inicia o servidor em uma thread separada."""
        try:
            # Import local para evitar recursão circular
            from api.manager import run_api_server
            self.log_action("STARTING_UVICORN", host=self.host, port=self.port)
            self.api_thread = threading.Thread(target=run_api_server, daemon=True)
            self.api_thread.start()
            self._server_started = True
        except Exception as e:
            self.log_error(e, "SERVER_START_FAILED")
            self._server_started = False

    def run_cycle(self, **kwargs) -> WorkerResult:
        violations = []
        score = 10
        metadata = {"host": self.host, "port": self.port}

        # Verifica se o servidor já foi iniciado
        if not self._server_started:
            self._start_server()
            # Aguarda um pouco para a porta abrir
            time.sleep(2)

        # Health Check por porta
        port_open = self._is_port_open()
        metadata["port_open"] = port_open

        if not port_open:
            violations.append(f"API port {self.port} is closed or unreachable.")
            score = -10
            
            # Se a thread morreu, tenta reiniciar
            if self.api_thread and not self.api_thread.is_alive():
                self.log_action("SERVER_THREAD_DIED", level="warning")
                self._start_server()
            else:
                self.log_action("PORT_CLOSED_BUT_THREAD_ALIVE", level="warning")
        else:
            # Se a porta está aberta, podemos assumir sucesso por enquanto
            self.log_action("HEALTH_CHECK_OK", port=self.port)

        status = "success" if not violations else "error"
        return WorkerResult(status=status, score=score, violations=violations, metadata=metadata)
