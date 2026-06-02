import logging
from typing import Any
from datetime import datetime

from core.subagent_base import SubAgentBase, tool
from core.worker_base import WorkerResult
from core.time_utils import now_utc
from core.database import SessionLocal
from core.models import Musica
from services import weather_service
from director.playlist_engine import playlist_engine_instance
from director.auditor import ProgrammingAuditor

logger = logging.getLogger("OmniCore.Workers.Playlist")

class PlaylistWorker(SubAgentBase):
    """
    Subagente de Playlist.
    Gera a programação da grade diária executando um ciclo de planejamento,
    auditoria de conformidade (crítica) e auto-correção iterativa.
    Pode gerar blocos específicos de 2h ou a grade diária de 24h completa.
    """
    def __init__(self, reward_store=None, config: dict[str, Any] | None = None):
        super().__init__(name="PlaylistWorker", reward_store=reward_store, config=config)
        self.auditor = ProgrammingAuditor()

    @tool
    def obter_clima_natal(self) -> str:
        """
        Consulta as condições meteorológicas em Natal/RN e retorna o 'Mood' correspondente
        ('Ensolarado', 'Sombrio', 'Foco').
        """
        try:
            return weather_service.get_natal_weather_mood()
        except Exception:
            return "Ensolarado"

    @tool
    def listar_musicas_candidatas(self, limit: int = 80) -> list:
        """
        Lista músicas candidatas disponíveis no acervo que não estão sob flag vermelha (redflag).
        Retorna uma lista de dicionários contendo caminho, título, artista, estilo e energia.
        """
        db = SessionLocal()
        try:
            tracks = (
                db.query(Musica)
                .filter(Musica.redflag == False)
                .order_by(Musica.vezes_tocada.asc(), Musica.ultima_reproducao.asc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "caminho": t.caminho,
                    "titulo": t.titulo,
                    "artista": t.artista,
                    "estilo": t.estilo,
                    "energia": t.energia,
                }
                for t in tracks if t.caminho
            ]
        finally:
            db.close()

    @tool
    def auditar_programacao(self, caminhos: list) -> dict:
        """
        Audita uma lista temporária de caminhos de arquivos M3U para verificar conformidade com regras.
        Retorna uma lista de strings contendo as violações encontradas. Se vazio, a playlist está 100% em conformidade.
        """
        import tempfile
        import os

        if not caminhos:
            return {"violations": ["A playlist fornecida está vazia."]}

        with tempfile.NamedTemporaryFile("w", encoding="cp1252", delete=False, suffix=".m3u") as tmp:
            tmp.write("#EXTM3U\n")
            for caminho in caminhos:
                tmp.write(f"{caminho}\n")
            tmp_path = tmp.name

        try:
            violations = self.auditor.audit_file(tmp_path)
            return {"violations": violations}
        except Exception as e:
            return {"violations": [f"Erro na auditoria: {e}"]}
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    @tool
    def gravar_playlist(self, caminhos: list, hora_inicio: int) -> str:
        """
        Persiste a playlist aprovada final no disco para execução do player (ZaraRadio)
        e atualiza o histórico de reprodução para rotatividade justa (Fair Rotation).
        Retorna uma mensagem de sucesso ou erro.
        """
        if not caminhos:
            return "Erro: Playlist vazia não pode ser gravada."
            
        try:
            from director import grade_rules as GR
            import os
            nome_arquivo = f"PROG_{hora_inicio:02d}H.m3u"
            caminho_completo = os.path.join(GR.CFG.get("pasta_programacao", "."), nome_arquivo)
            
            os.makedirs(os.path.dirname(caminho_completo), exist_ok=True)
            with open(caminho_completo, "w", encoding="cp1252", errors="replace") as f:
                f.write("#EXTM3U\n")
                for caminho in caminhos:
                    f.write(f"{caminho}\n")
                    
            # Atualiza o banco de dados marcando as músicas como tocadas
            db = SessionLocal()
            try:
                from core.time_utils import now_utc
                agora = now_utc()
                db.query(Musica).filter(Musica.caminho.in_(caminhos)).update(
                    {
                        Musica.ultima_reproducao: agora,
                        Musica.vezes_tocada: Musica.vezes_tocada + 1
                    },
                    synchronize_session=False,
                )
                db.commit()
            except Exception as dbe:
                logger.error(f"Erro ao salvar reproduções no banco durante gravar_playlist: {dbe}")
                db.rollback()
            finally:
                db.close()
                
            return f"Playlist gravada com sucesso em: {caminho_completo}"
        except Exception as e:
            return f"Erro ao gravar playlist no disco: {e}"

    def _gerar_bloco_unico(self, hora_inicio: int, mood: str | None) -> dict:
        self.log_action("PLAYLIST_GEN_START", hora=hora_inicio)
        
        system_prompt = (
            "Você é o Subagente de Programação Artística (Playlist Engine) do Omni Core V2.\n"
            "Seu trabalho é gerar uma playlist de 2 horas (aproximadamente 20 a 25 músicas) livre de violações.\n"
            "Regras e Constraints do Canal:\n"
            "- Não repita o mesmo artista de forma consecutiva ou muito próxima.\n"
            "- Adapte as faixas ao clima/mood atual da rádio.\n"
            "Fluxo de Trabalho Obrigatório:\n"
            "1. Se o mood não for fornecido, chame 'obter_clima_natal' para definir o mood climático atual.\n"
            "2. Chame 'listar_musicas_candidatas' para obter a lista de músicas utilizáveis.\n"
            "3. Proponha uma lista ordenada de caminhos de arquivos e chame 'auditar_programacao' para validar.\n"
            "4. Se houver violações na auditoria, altere e otimize a playlist proposta (substituindo faixas que causam problemas) e audite novamente.\n"
            "5. Quando a playlist estiver perfeitamente validada (ou caso esgote as tentativas de otimização), chame 'gravar_playlist' para salvar.\n"
            "Importante: Você DEVE retornar os caminhos exatos que obteve da lista de candidatas."
        )

        task = f"Montar e auditar grade de programação artística para o bloco de {hora_inicio:02d}H. Mood desejado inicial: {mood}"

        try:
            res = self.run_agent_loop(task, system_prompt, max_steps=5)
            if res.get("status") == "success":
                return {"status": "success", "result": res.get("result"), "violations": []}
            else:
                return {
                    "status": "failed", 
                    "violations": [f"Subagente falhou em gerar playlist estável para o bloco {hora_inicio:02d}H: {res.get('result')}"]
                }
        except Exception as e:
            return {"status": "failed", "violations": [f"Erro crítico no bloco {hora_inicio:02d}H: {str(e)}"]}

    def run_cycle(self, hora_inicio: int | None = None, mood: str | None = None) -> WorkerResult:
        if hora_inicio is None:
            # Geração diária completa de 24h (todos os 12 blocos de 2h)
            self.log_action("PLAYLIST_DAILY_GEN_START")
            
            # Sincroniza acervo e boletins/jornais no início do ciclo diário
            from services.acervo_sync import sync_acervo
            try:
                sync_acervo()
            except Exception as se:
                self.log_error(se, "PRE_GEN_SYNC_ACERVO_FAILED")

            erros = 0
            sucessos = 0
            metadata_blocos = {}
            violations = []

            for hora in range(0, 24, 2):
                res_bloco = self._gerar_bloco_unico(hora, mood)
                if res_bloco["status"] == "success":
                    sucessos += 1
                else:
                    erros += 1
                    violations.extend(res_bloco["violations"])
                metadata_blocos[f"{hora:02d}H"] = res_bloco

            status = "success" if erros == 0 else ("partial_success" if sucessos > 0 else "failed")
            score = sucessos * 10 - erros * 5
            
            metadata = {
                "sucessos": sucessos,
                "erros": erros,
                "generated_at": now_utc().isoformat(),
                "blocos": metadata_blocos
            }
            
            # Registrar no AutopilotLog
            from services.autopilot_service import autopilot_service
            db = SessionLocal()
            try:
                msg = f"Geração automática de programação diária 24h concluída. {sucessos} blocos com sucesso, {erros} erros."
                autopilot_service.log_action(db, "PLAYLIST_GEN", msg, success=(erros == 0))
            except Exception as le:
                logger.error(f"Erro ao registrar log de geração automática no AutopilotLog: {le}")
            finally:
                db.close()
                
            return WorkerResult(status=status, score=score, violations=violations, metadata=metadata)
        else:
            # Geração de um bloco de 2h individual
            res_bloco = self._gerar_bloco_unico(hora_inicio, mood)
            if res_bloco["status"] == "success":
                return WorkerResult(
                    status="success", 
                    score=15, 
                    metadata={
                        "hora_inicio": hora_inicio,
                        "generated_at": now_utc().isoformat(),
                        "agent_log": res_bloco["result"]
                    }
                )
            else:
                return WorkerResult(
                    status="failed",
                    score=-5,
                    violations=res_bloco["violations"],
                    metadata={"hora_inicio": hora_inicio, "generated_at": now_utc().isoformat()}
                )
