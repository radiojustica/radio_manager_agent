"""
UpdateWorker - Verifica e aplica atualizações do sistema automaticamente.
Roda periodicamente (a cada 1 hora) e reconstrói o EXE se houver mudanças no código.
"""

import os
import shutil
import hashlib
import logging
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from core.worker_base import WorkerBase, WorkerResult
from services.guardian_service import guardian_instance

logger = logging.getLogger("OmniCore.UpdateWorker")

class UpdateWorker(WorkerBase):
    def __init__(self, name: str = "UpdateWorker", reward_store=None, config: dict[str, Any] | None = None):
        super().__init__(name=name, reward_store=reward_store, config=config)
        self.base_path = Path(__file__).resolve().parent.parent
        self.dist_path = self.base_path / "dist"
        self.code_hash_file = self.dist_path / "code.md5"
        self.exe_path = self.dist_path / "omni_core.exe"
        
    def _calculate_code_hash(self) -> str:
        """Calcula hash MD5 do código-fonte (excluindo __pycache__)."""
        hasher = hashlib.md5()
        
        # Arquivos/diretórios a verificar
        to_check = [
            self.base_path / "main.py",
            self.base_path / "core",
            self.base_path / "api",
            self.base_path / "gui",
            self.base_path / "workers",
            self.base_path / "routers",
            self.base_path / "services",
            self.base_path / "worker_manager.py",
        ]
        
        for path in to_check:
            if not path.exists():
                continue
                
            if path.is_file():
                with open(path, 'rb') as f:
                    hasher.update(f.read())
            else:
                for file_path in sorted(path.rglob("*.py")):
                    if "__pycache__" not in str(file_path):
                        with open(file_path, 'rb') as f:
                            hasher.update(f.read())
        
        return hasher.hexdigest()
    
    def _check_for_updates(self) -> bool:
        """Verifica se há mudanças no código."""
        current_hash = self._calculate_code_hash()
        
        if self.code_hash_file.exists():
            stored_hash = self.code_hash_file.read_text().strip()
            if current_hash == stored_hash:
                logger.info("✓ Código sem mudanças. Nenhuma atualização necessária.")
                return False
        
        logger.info(f"🔄 Mudanças detectadas no código (hash: {current_hash})")
        return True
    
    def _rebuild_exe(self) -> bool:
        """Reconstrói o EXE usando build.py."""
        try:
            logger.info("🔨 Reconstruindo EXE...")
            build_script = self.base_path / "build.py"
            
            if not build_script.exists():
                logger.error("build.py não encontrado")
                return False
            
            # Executa build.py em subprocess
            result = subprocess.run(
                [
                    "python",
                    str(build_script)
                ],
                cwd=str(self.base_path),
                capture_output=True,
                timeout=300  # 5 minutos
            )
            
            if result.returncode != 0:
                logger.error(f"Erro no build: {result.stderr.decode()}")
                return False
            
            logger.info("✓ EXE reconstruído com sucesso")
            
            # Atualiza hash armazenado
            current_hash = self._calculate_code_hash()
            self.code_hash_file.write_text(current_hash)
            
            return True
        except subprocess.TimeoutExpired:
            logger.error("Build expirou (timeout 5min)")
            return False
        except Exception as e:
            logger.error(f"Erro ao reconstruir EXE: {e}")
            return False
    
    def run_cycle(self) -> WorkerResult:
        """Executa o ciclo de verificação e atualização."""
        try:
            # Cria diretório dist se não existir
            self.dist_path.mkdir(exist_ok=True, parents=True)
            
            # Verifica se há mudanças
            if not self._check_for_updates():
                return WorkerResult(status="success", score=1, violations=[], metadata={"action": "no_update"})
            
            # Reconstrói EXE
            if self._rebuild_exe():
                logger.info("✅ Sistema atualizado com sucesso!")
                
                # Notifica via Telegram
                try:
                    guardian_instance.notifier.send_alert("UPDATE", {
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "message": "Omni Core atualizado. Nova versão em uso na próxima reinicialização."
                    })
                except:
                    pass
                
                return WorkerResult(
                    status="success",
                    score=2,
                    violations=[],
                    metadata={"action": "updated", "exe_path": str(self.exe_path)}
                )
            else:
                return WorkerResult(
                    status="failed",
                    score=-5,
                    violations=["Build falhou"],
                    metadata={"action": "build_failed"}
                )
        
        except Exception as e:
            logger.error(f"Erro crítico no UpdateWorker: {e}")
            return WorkerResult(
                status="failed",
                score=-3,
                violations=[f"Erro: {str(e)}"],
                metadata={"action": "error", "error": str(e)}
            )
