import os
import logging
import asyncio
from datetime import datetime
from typing import Any

from core.subagent_base import SubAgentBase, tool
from core.worker_base import WorkerResult
from core.reward import RewardStore
from core.database import SessionLocal, init_db
from core.models import Musica
from services.curadoria_worker import processar_arquivo

logger = logging.getLogger("OmniCore.Workers.Curadoria")

class CuradoriaWorker(SubAgentBase):
    """
    Subagente de Curadoria.
    Realiza a curadoria acústica de novas faixas, classifica humor (Mood) e
    gerencia quarentena (redflag) de músicas com base em decisões de raciocínio.
    """
    def __init__(self, reward_store: RewardStore | None = None, config: dict[str, Any] | None = None):
        super().__init__(name="CuradoriaWorker", reward_store=reward_store, config=config)
        self.batch_size = self.config.get("batch_size", 3)

    @tool
    def auditar_arquivo_acustica(self, musica_id: int, caminho: str) -> dict:
        """
        Executa a auditoria acústica física do arquivo mp3 para calcular duração, BPM e energia.
        Retorna um dicionário com os dados acústicos ou status de quarentena.
        """
        try:
            resultado = processar_arquivo(musica_id, caminho)
            return resultado
        except Exception as e:
            return {"status": "ERROR", "motivo": str(e)}

    @tool
    def salvar_curadoria(self, musica_id: int, mood: str, energia: int, bpm: int, valence: float, danceability: float) -> str:
        """
        Salva a classificação final e metadados acústicos da música no banco de dados.
        Use apenas se a música não apresentar anomalias (redflags).
        """
        db = SessionLocal()
        try:
            musica = db.query(Musica).filter(Musica.id == musica_id).first()
            if not musica:
                return f"Erro: Música com ID {musica_id} não encontrada."
            
            musica.auditado_acustica = True
            musica.mood = mood
            musica.energia = energia
            musica.bpm = bpm
            musica.valence = valence
            musica.danceability = danceability
            musica.redflag = False
            db.commit()
            return f"Curadoria salva com sucesso para a música {musica_id}."
        except Exception as e:
            db.rollback()
            return f"Erro ao salvar no banco: {e}"
        finally:
            db.close()

    @tool
    def enviar_quarentena(self, musica_id: int, motivo: str) -> str:
        """
        Envia uma música para a quarentena (redflag), definindo o motivo da falha de integridade acústica.
        """
        db = SessionLocal()
        try:
            musica = db.query(Musica).filter(Musica.id == musica_id).first()
            if not musica:
                return f"Erro: Música com ID {musica_id} não encontrada."
            
            musica.auditado_acustica = True
            musica.redflag = True
            musica.quarantine_reason = motivo
            db.commit()
            return f"Música {musica_id} colocada em quarentena com sucesso. Motivo: {motivo}"
        except Exception as e:
            db.rollback()
            return f"Erro ao enviar para quarentena: {e}"
        finally:
            db.close()

    @tool
    def normalizar_tags_id3(self, caminho: str | None = None) -> dict:
        """
        Normaliza o encoding das tags ID3 (título, artista, álbum) de um arquivo MP3
        ou de todo o acervo para compatibilidade com ZaraRadio (Windows-1252/cp1252).
        Se 'caminho' for None, processa todo o acervo de músicas.
        Corrige mojibake do tipo 'MÃ¡rcia → Márcia' automaticamente.
        """
        try:
            from scripts.fix_id3_encoding import normalizar_id3_arquivo, processar_acervo
            if caminho:
                resultado = normalizar_id3_arquivo(caminho, dry_run=False)
                return resultado
            else:
                from director import grade_rules as GR
                pasta = GR.CFG.get("pasta_musicas", r"D:\RADIO\MUSICAS")
                resultado = processar_acervo(pasta, dry_run=False)
                return resultado
        except Exception as e:
            return {"status": "erro", "motivo": str(e)}

    def run_cycle(self, **kwargs) -> WorkerResult:
        init_db()
        db = SessionLocal()
        violations = []
        metadata = {"processed_count": 0, "quarantined_count": 0, "moods_classified": 0, "errors": 0}
        score = 0

        try:
            # Seleciona músicas pendentes de curadoria completa (acústica ou mood)
            pendentes = db.query(Musica).filter(
                (Musica.auditado_acustica == False) | 
                ((Musica.auditado_acustica == True) & (Musica.redflag == False) & (Musica.mood == None))
            ).order_by(Musica.id.asc()).limit(self.batch_size).all()

            if not pendentes:
                return WorkerResult(status="idle", score=1, metadata={"message": "Nenhuma música pendente."})

            system_prompt = (
                "Você é o Subagente Curador da Rádio. Seu papel é fazer a auditoria acústica e a curadoria de novas faixas.\n"
                "Instruções:\n"
                "1. Se a música não foi auditada acusticamente (auditado_acustica = False), você deve chamar 'auditar_arquivo_acustica'.\n"
                "2. Se a auditoria acústica retornar status 'QUARANTINED', você deve chamar 'enviar_quarentena' imediatamente com o motivo.\n"
                "3. Caso contrário, você deve classificar o 'mood' ('Ensolarado', 'Sombrio', 'Foco') com base no título/artista e salvar os dados via 'salvar_curadoria'.\n"
                "Seja conciso no pensamento e execute as ações de forma direta."
            )

            for musica in pendentes:
                task = (
                    f"Fazer a curadoria de: ID {musica.id} | Artista: {musica.artista} | Título: {musica.titulo} | Caminho: {musica.caminho}\n"
                    f"Estado atual: Auditado={musica.auditado_acustica}, Mood={musica.mood}, Redflag={musica.redflag}"
                )
                
                try:
                    # Executa o loop do agente
                    res = self.run_agent_loop(task, system_prompt, max_steps=5)
                    
                    if res.get("status") == "success":
                        metadata["processed_count"] += 1
                        score += 5
                        
                        # Recarrega para verificação de logs no resultado
                        db.refresh(musica)
                        if musica.redflag:
                            metadata["quarantined_count"] += 1
                            violations.append(f"Música {musica.id} ({musica.titulo}) enviada para quarentena: {musica.quarantine_reason}")
                        else:
                            metadata["moods_classified"] += 1
                    else:
                        metadata["errors"] += 1
                        violations.append(f"Subagente falhou em processar música {musica.id}: {res.get('result')}")
                        score -= 2
                except Exception as e:
                    logger.error(f"Erro ao processar música {musica.id} no loop do agente: {e}")
                    metadata["errors"] += 1
                    score -= 5
                    violations.append(f"Erro crítico no processamento de {musica.id}: {str(e)}")

            status = "success" if metadata["errors"] == 0 else "partial_success"
            return WorkerResult(status=status, score=score, violations=violations, metadata=metadata)

        except Exception as e:
            logger.error(f"Falha crítica no ciclo de curadoria: {e}")
            return WorkerResult(status="error", score=-10, violations=[str(e)], metadata=metadata)
        finally:
            db.close()
