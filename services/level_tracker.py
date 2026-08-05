"""
Tracker de nível acústico em tempo real (somente leitura).

Mantém uma janela deslizante das últimas amostras de dB (pico da placa USB de
transmissão) e deriva métricas REAIS a partir do áudio de verdade:

  - short_term_lufs: loudness curto-prazo estimado (média de potência na janela,
    convertida de volta para dB). Não é o LUFS integrado formal (BS.1770 exige
    filtro K-weighting + janela de 3s), mas é um valor REAL derivado do sinal,
    não um mock.
  - dynamic_range: diferença entre o pico e a média na janela (em dB).

Nenhuma dessas métricas altera áudio nem volume — apenas observa.
"""

import math
import threading
import time
from collections import deque


class LevelTracker:
    def __init__(self, window_seconds: float = 8.0, sample_rate_hz: float = 2.0):
        self.window_seconds = window_seconds
        self.max_samples = max(8, int(window_seconds * sample_rate_hz))
        self._buffer = deque(maxlen=self.max_samples)
        self._lock = threading.Lock()
        self._last = {"db": -60.0, "lufs_st": None, "dr": None, "updated_at": 0.0}

    def feed(self, db: float):
        """Registra uma amostra de dB (pico instantâneo). Thread-safe."""
        if db is None or db <= -100:
            db = -60.0
        with self._lock:
            self._buffer.append(db)
            self._last = self._compute_locked()

    def _compute_locked(self) -> dict:
        if not self._buffer:
            return {"db": -60.0, "lufs_st": None, "dr": None, "updated_at": time.time()}
        samples = list(self._buffer)
        # Converte dB -> potência linear (ref 1.0), média, volta p/ dB.
        powers = [10.0 ** (d / 20.0) for d in samples if d > -100]
        if powers:
            mean_power = sum(powers) / len(powers)
            lufs_st = 20.0 * math.log10(mean_power) if mean_power > 0 else -60.0
        else:
            lufs_st = -60.0
        peak = max(samples)
        dr = peak - lufs_st  # pico menos média de potência -> proxy de range dinâmico
        if dr < 0:
            dr = 0.0
        return {
            "db": samples[-1],
            "lufs_st": round(lufs_st, 1),
            "dr": round(dr, 1),
            "updated_at": time.time(),
        }

    def snapshot(self) -> dict:
        with self._lock:
            return dict(self._last)


# Instância global (uma por processo) — alimentada a cada poll de /api/status/player/now
level_tracker = LevelTracker()
