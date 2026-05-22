import time
import threading
from collections import deque

class RateLimiter:
    """
    Controlador de taxa thread-safe simples para limitar chamadas a serviços externos
    (como APIs de IA e envio de mensagens).
    """
    def __init__(self, max_calls: int, period_seconds: float):
        self.max_calls = max_calls
        self.period = period_seconds
        self._calls = deque()
        self._lock = threading.Lock()
    
    def acquire(self) -> bool:
        with self._lock:
            now = time.monotonic()
            # Remove chamadas fora da janela de tempo
            while self._calls and now - self._calls[0] > self.period:
                self._calls.popleft()
            if len(self._calls) >= self.max_calls:
                return False
            self._calls.append(now)
            return True
    
    def wait_and_acquire(self):
        while not self.acquire():
            time.sleep(0.5)
