import os
import sys
import subprocess
import logging
from typing import Any
from pathlib import Path
from core.worker_base import WorkerBase, WorkerResult

logger = logging.getLogger("OmniCore.Worker.ContentGenerationWorker")

class ContentGenerationWorker(WorkerBase):
    def __init__(self, reward_store: Any | None = None, config: dict[str, Any] | None = None):
        super().__init__(name="ContentGenerationWorker", reward_store=reward_store, config=config)
        
        # Mapeamento do diretório do projeto radio_ia
        # O repositório zipado foi extraído em scratch/radio_ia-main/radio_ia-main
        self.radio_ia_root = Path(r"C:\Users\STREAMING\.gemini\antigravity\scratch\radio_ia-main\radio_ia-main")
        
        # Fallback alternativo caso tenha sido movido ou renomeado
        if not self.radio_ia_root.exists():
            sibling_dir = Path(__file__).resolve().parent.parent.parent / "radio_ia-main" / "radio_ia-main"
            if sibling_dir.exists():
                self.radio_ia_root = sibling_dir

    def run_cycle(self, **kwargs) -> WorkerResult:
        """Executa a geração de áudio física por IA via subprocesso."""
        self.log_action("GENERATION_START")
        
        if not self.radio_ia_root.exists():
            err_msg = f"Diretório raiz da Fábrica de IA não encontrado: {self.radio_ia_root}"
            logger.error(err_msg)
            return WorkerResult(
                status="error",
                score=-5,
                violations=[err_msg],
                metadata={"error": err_msg}
            )

        from core.database import SessionLocal
        from services.autopilot_service import autopilot_service
        db = SessionLocal()
        
        # Determinar qual python usar (preferencialmente o venv local do radio_ia)
        python_exe = sys.executable
        venv_python = self.radio_ia_root / "venv" / "Scripts" / "python.exe"
        if venv_python.exists():
            python_exe = str(venv_python)
            logger.info(f"Usando ambiente virtual do radio_ia: {python_exe}")
        
        violations = []
        metadata = {
            "boletins_njud_generation": {},
            "giro_generation": {}
        }
        
        # 1. Executar Agente IA (Boletins e NJUD)
        script_agente = self.radio_ia_root / "modules" / "agente" / "agente_ia.py"
        if script_agente.exists():
            logger.info("Disparando pipeline cognitivo e de gravação (agente_ia.py)...")
            try:
                # O agente_ia.py espera a flag --once ou --daemon
                res = subprocess.run(
                    [python_exe, str(script_agente), "--once"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="ignore",
                    cwd=str(self.radio_ia_root)
                )
                
                success = res.returncode == 0
                metadata["boletins_njud_generation"] = {
                    "success": success,
                    "returncode": res.returncode,
                    "stdout": res.stdout[-1000:] if res.stdout else "", # Mantém apenas os últimos 1000 caracteres
                    "stderr": res.stderr[-1000:] if res.stderr else ""
                }
                
                if not success:
                    violations.append(f"Agente IA (Boletins/NJUD) falhou com código {res.returncode}")
                    autopilot_service.log_action(db, "GENERATE_CONTENT", f"Falha na geração de Boletins/NJUD (returncode {res.returncode})", success=False)
                else:
                    logger.info("Pipeline do Agente IA (Boletins/NJUD) concluído com sucesso.")
                    autopilot_service.log_action(db, "GENERATE_CONTENT", "Geração de Boletins/NJUD concluída com sucesso via subprocesso.", success=True)
            except Exception as e:
                err_str = f"Erro ao executar agente_ia.py: {str(e)}"
                logger.error(err_str)
                violations.append(err_str)
                metadata["boletins_njud_generation"] = {"success": False, "error": str(e)}
                autopilot_service.log_action(db, "GENERATE_CONTENT", f"Erro crítico ao disparar pipeline de Boletins/NJUD: {str(e)}", success=False)
        else:
            violations.append(f"Script do Agente IA não encontrado em {script_agente}")

        # 2. Executar Giro nas Comarcas (giro_pipeline.py)
        script_giro = self.radio_ia_root / "modules" / "giro" / "giro_pipeline.py"
        if script_giro.exists():
            logger.info("Disparando pipeline do Giro nas Comarcas (giro_pipeline.py)...")
            try:
                res = subprocess.run(
                    [python_exe, str(script_giro)],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="ignore",
                    cwd=str(self.radio_ia_root)
                )
                
                success = res.returncode == 0
                metadata["giro_generation"] = {
                    "success": success,
                    "returncode": res.returncode,
                    "stdout": res.stdout[-1000:] if res.stdout else "",
                    "stderr": res.stderr[-1000:] if res.stderr else ""
                }
                
                if not success:
                    violations.append(f"Giro nas Comarcas falhou com código {res.returncode}")
                    autopilot_service.log_action(db, "GENERATE_GIRO", f"Falha na geração do Giro (returncode {res.returncode})", success=False)
                else:
                    logger.info("Pipeline do Giro nas Comarcas concluído com sucesso.")
                    autopilot_service.log_action(db, "GENERATE_GIRO", "Geração do Giro nas Comarcas concluída com sucesso via subprocesso.", success=True)
            except Exception as e:
                err_str = f"Erro ao executar giro_pipeline.py: {str(e)}"
                logger.error(err_str)
                violations.append(err_str)
                metadata["giro_generation"] = {"success": False, "error": str(e)}
                autopilot_service.log_action(db, "GENERATE_GIRO", f"Erro crítico ao disparar pipeline do Giro nas Comarcas: {str(e)}", success=False)
        else:
            violations.append(f"Script do Giro não encontrado em {script_giro}")
            
        db.close()

        if violations:
            return WorkerResult(
                status="error",
                score=-5,
                violations=violations,
                metadata=metadata
            )
            
        message = "Geração de conteúdo por IA concluída com sucesso para todas as mídias."
        metadata["message"] = message
        return WorkerResult(
            status="success",
            score=5,
            metadata=metadata
        )
