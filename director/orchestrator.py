"""
Director Orchestrator — Omni Core V2
=====================================
O "Cérebro" que comanda a direção musical. 
Coordena a geração da grade, chama a auditoria e garante que o perfil seja cumprido.
"""

import os
import logging
from director.profile import PROFILE
from director.auditor import ProgrammingAuditor
from services.guardian_service import guardian_instance

logger = logging.getLogger("OmniCore.Director")

class MusicDirector:
    def __init__(self):
        self.auditor = ProgrammingAuditor()
        self.profile = PROFILE

    def approve_or_redo(self, m3u_path: str, hour: int) -> bool:
        """Audita um arquivo M3U recém-gerado. Se reprovar, tenta gerar novamente."""
        logger.info(f"[Director] Auditando bloco {hour:02d}H em {os.path.basename(m3u_path)}...")
        
        violations = self.auditor.audit_file(m3u_path)
        
        if not violations:
            logger.info(f"[Director] Bloco {hour:02d}H aprovado com sucesso.")
            return True

        # Se chegou aqui, há violações
        logger.warning(f"[Director] Bloco {hour:02d}H reprovado! Detecatadas {len(violations)} violações.")
        
        if self.profile["policy"]["auto_redo_on_violation"]:
            return self._handle_regeneration(m3u_path, hour)
        
        return False

    def _handle_regeneration(self, m3u_path: str, hour: int) -> bool:
        max_retries = self.profile["policy"]["max_retries"]
        from director.playlist_engine import playlist_engine_instance
        
        for attempt in range(1, max_retries + 1):
            logger.info(f"[Director] Tentativa de regeneração {attempt}/{max_retries} para o bloco {hour:02d}H...")
            
            # Remove o histórico recente para o motor não travar nas mesmas músicas
            # e forçar um novo sorteio dentro da janela de prioridade
            playlist_engine_instance.gerar_playlist_bloco(hour)
            
            new_violations = self.auditor.audit_file(m3u_path)
            if not new_violations:
                logger.info(f"[Director] Sucesso! Bloco {hour:02d}H estabilizado na tentativa {attempt}.")
                guardian_instance.log_event("DIRECTOR", f"Bloco {hour:02d}H regenerado e aprovado.")
                return True
        
        logger.error(f"[Director] Falha crítica: Bloco {hour:02d}H não pôde ser estabilizado após {max_retries} tentativas.")
        if self.profile["policy"]["alert_on_failure"]:
            guardian_instance.log_event("ERROR", f"DIREÇÃO MUSICAL: Falha em estabilizar bloco {hour:02d}H")
        
        return False

    def audit_all_daily_logs(self):
        """Varre os logs de execução da rádio para verificar conformidade histórica."""
        # TODO: Implementar leitura de D:\RADIO\LOG ZARARADIO\yyyy-mm-dd.log
        pass

# Instância única do Diretor
music_director_instance = MusicDirector()


