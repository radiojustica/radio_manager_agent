import os
from typing import Any

from core.worker_base import WorkerBase, WorkerResult
from director.auditor import ProgrammingAuditor
from director import grade_rules as GR


class AuditWorker(WorkerBase):
    def __init__(self, name: str = "AuditWorker", reward_store=None, config: dict[str, Any] | None = None):
        super().__init__(name=name, reward_store=reward_store, config=config)
        self.auditor = ProgrammingAuditor()

    def _find_playlists(self) -> list[str]:
        folder = GR.CFG.get("pasta_programacao")
        if not folder:
            return []
        if not os.path.exists(folder):
            return []
        return [
            os.path.join(folder, f)
            for f in os.listdir(folder)
            if f.upper().endswith(".M3U") and f.startswith("PROG_")
        ]

    def run_cycle(self, audit_path: str | None = None) -> WorkerResult:
        targets = [audit_path] if audit_path else self._find_playlists()
        violations: list[str] = []
        audited = 0

        for path in targets:
            if not path or not os.path.exists(path):
                violations.append(f"Arquivo não encontrado: {path}")
                continue
            result = self.auditor.audit_file(path)
            if result:
                violations.extend([str(item) for item in result])
            audited += 1

        score = 1 if not violations else -len(violations)
        status = "success" if not violations else "failed"
        metadata: dict[str, Any] = {
            "audited_files": audited,
            "paths": targets,
        }
        return WorkerResult(status=status, score=score, violations=violations, metadata=metadata)
