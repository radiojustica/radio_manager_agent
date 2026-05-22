from __future__ import annotations

import json
import logging
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

logger = logging.getLogger("OmniCore.Reward")

import os
import sys

DATA_DIR = Path(r"D:\RADIO")
try:
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

DEFAULT_REWARD_STORE_PATH = DATA_DIR / "worker_rewards.json"


class RewardStore:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path is not None else DEFAULT_REWARD_STORE_PATH
        self.reward_logger = logging.getLogger("OmniCore.Reward.Store")
        self.data = self._load()

    def _load(self) -> dict[str, Any]:
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                if isinstance(payload, dict):
                    self.reward_logger.info(f"Reward store carregado de {self.path}")
                    return payload
            except Exception as e:
                self.reward_logger.error(f"Falha ao carregar reward store: {e}")
        self.reward_logger.info(f"Reward store inicializado vazio em {self.path}")
        return {"workers": {}, "history": []}

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
            self.reward_logger.debug(f"Reward store salvo em {self.path}")
        except Exception as e:
            self.reward_logger.error(f"Falha ao salvar reward store: {e}")

    def record(self, worker_name: str, score: int, violations: list[str] | None = None, metadata: dict[str, Any] | None = None) -> None:
        violations = violations or []
        metadata = metadata or {}
        timestamp = datetime.now(UTC).isoformat()
        
        record = {
            "worker": worker_name,
            "timestamp": timestamp,
            "score": score,
            "violations": violations,
            "metadata": metadata,
        }

        # Atualiza dados do worker
        self.data.setdefault("workers", {})
        self.data["workers"].setdefault(worker_name, {"score_total": 0, "cycles": 0, "last_result": None, "history": []})

        worker_data = self.data["workers"][worker_name]
        worker_data["score_total"] += score
        worker_data["cycles"] += 1
        worker_data["last_result"] = {"score": score, "violations": violations, "metadata": metadata, "timestamp": timestamp}
        
        # Histórico persistente por worker (rolling log de 20 entradas)
        worker_data["history"] = (worker_data.get("history", []) + [record])[-20:]

        # Histórico global limitado (últimas 1000 entradas)
        self.data["history"] = (self.data.get("history", []) + [record])[-1000:]

        self.save()
        
        self.reward_logger.info(
            f"[{worker_name}] Reward recorded: score={score}, total={worker_data['score_total']}",
            extra={"worker": worker_name, "score": score, "total": worker_data["score_total"], "timestamp": timestamp}
        )

    def summary(self) -> dict[str, Any]:
        """Retorna resumo dos scores de todos os workers."""
        return self.data.get("workers", {})

    def latest(self, worker_name: str) -> dict[str, Any] | None:
        """Retorna o último resultado de um worker específico."""
        return self.data.get("workers", {}).get(worker_name)

    def history(self, worker_name: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        """Retorna histórico de rewards, opcionalmente filtrado por worker."""
        if worker_name:
            worker_data = self.data.get("workers", {}).get(worker_name, {})
            # Tenta usar o histórico persistente por worker (rolling log)
            if "history" in worker_data:
                records = worker_data["history"][-limit:]
            else:
                # Fallback para scan global (migração)
                records = [h for h in self.data.get("history", []) if h.get("worker") == worker_name][-limit:]
        else:
            records = self.data.get("history", [])[-limit:]
            
        # Adiciona descrições amigáveis
        for r in records:
            r["description"] = self.generate_description(r)
        return records

    @staticmethod
    def generate_description(record: dict[str, Any]) -> str:
        """Gera uma descrição legível para humanos baseada no worker e metadados."""
        worker = record.get("worker")
        metadata = record.get("metadata", {})
        violations = record.get("violations", [])
        score = record.get("score", 0)
        
        if worker == "GuardianWorker":
            procs = metadata.get("processes", {})
            zara = procs.get("zararadio", "Desconhecido")
            butt = procs.get("butt", "Desconhecido")
            silence = metadata.get("silence_seconds", 0)
            desc = f"Monitoramento: ZaraRadio ({zara}), BUTT ({butt}). Silêncio detectado: {silence}s."
            if violations:
                desc += f" Ocorrências: {', '.join(violations)}"
            return desc
        
        if worker == "ButtWorker":
            recon = metadata.get("reconnected", 0)
            total = metadata.get("total_instances", 0)
            if recon > 0:
                return f"Reconexão BUTT: {recon} de {total} instâncias foram restauradas."
            return f"Status BUTT estável: {total} instâncias monitoradas."
        
        if worker == "CuradoriaWorker":
            msg = metadata.get("message", "")
            added = metadata.get("added_count", 0)
            if added > 0:
                return f"Curadoria: {added} novas faixas adicionadas ao acervo."
            return msg or "Ciclo de curadoria: Nenhuma alteração necessária."

        if worker == "DownloaderWorker":
            success = metadata.get("success_count", 0)
            failed = metadata.get("failed_count", 0)
            if success > 0 or failed > 0:
                return f"Downloads: {success} concluídos, {failed} falhas."
            return "Downloads: Fila vazia."
            
        if worker == "WeatherWorker":
            temp = metadata.get("temp", "N/A")
            cond = metadata.get("condition", "N/A")
            return f"Clima atualizado: {temp}C, {cond}."

        # Genérico para workers não mapeados
        if score < 0:
            msg = f"Worker {worker} reportou falhas"
            if violations:
                msg += f" ({', '.join(violations)})"
            return msg + "."
            
        if violations:
            return f"Ação de {worker} concluída com avisos: {', '.join(violations)}."
        
        return f"O worker {worker} completou sua tarefa com sucesso (Score: {score})."
