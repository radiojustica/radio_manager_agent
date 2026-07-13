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
from services.pubsub_service import pubsub_service_instance

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
    def obter_informacoes_contexto(self, hora_inicio: int) -> dict:
        """
        Retorna informações detalhadas do contexto operacional para o bloco atual:
        - Clima atual em Natal/RN e o Mood padrão associado.
        - Mês atual (para sazonalidade, ex: 6 para junho).
        - Dia da semana atual (0=Segunda, 6=Domingo).
        - Estilos de música sugeridos por default para cada Mood.
        - Regra padrão de energia sugerida para o bloco.
        """
        from datetime import datetime
        from core.time_utils import now_local
        from services import weather_service
        from director import grade_rules as GR
        
        try:
            mood = weather_service.get_natal_weather_mood()
        except Exception:
            mood = "Ensolarado"
            
        now = now_local()
        mes_atual = now.month
        dia_semana = now.weekday()
        
        # Mapeamento de moods
        moods_estilos = {
            m: GR.estilos_para_mood(m) for m in ["Ensolarado", "Nublado", "Chuvoso"]
        }
        
        # Obter limites sugeridos de energia
        energia_sugerida = GR.obter_regras_energia_por_hora(hora_inicio)
        
        return {
            "clima_mood_natal": mood,
            "hora_bloco": hora_inicio,
            "mes_atual": mes_atual,
            "dia_semana": dia_semana,
            "energia_sugerida": energia_sugerida,
            "moods_estilos_default": moods_estilos
        }

    @tool
    def listar_musicas_candidatas(self, limit: int = 80, tema_preferencial: str | None = None) -> list:
        """
        Lista músicas candidatas disponíveis no acervo que não estão sob flag vermelha (redflag).
        Se tema_preferencial for fornecido (ex: 'junho'), prioriza músicas com esse tema.
        Retorna uma lista de dicionários contendo caminho, título, artista, estilo e energia.
        """
        db = SessionLocal()
        try:
            query = db.query(Musica).filter(Musica.redflag == False)
            
            if tema_preferencial:
                # Ordena primeiro as músicas com o tema pedido e então pela rotatividade
                query = query.order_by(
                    (Musica.tema_especial == tema_preferencial).desc(),
                    Musica.vezes_tocada.asc(), 
                    Musica.ultima_reproducao.asc()
                )
            else:
                query = query.order_by(
                    Musica.vezes_tocada.asc(), 
                    Musica.ultima_reproducao.asc()
                )
                
            tracks = query.limit(limit).all()
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
            
            try:
                pubsub_service_instance.publish("auditoria:bloco_gerado", {
                    "hora_inicio": hora_inicio,
                    "mood": "Desconhecido",
                    "caminho_m3u": os.path.abspath(caminho_completo),
                    "timestamp": now_utc().isoformat(),
                    "status": "success"
                })
            except Exception as pe:
                logger.error(f"Erro ao publicar no PubSub na gravação: {pe}")
                
            return f"Playlist gravada com sucesso em: {caminho_completo}"
        except Exception as e:
            return f"Erro ao gravar playlist no disco: {e}"

    @tool
    def gerar_playlist_via_motor(self, hora_inicio: int, mood: str | None = None, estilos: list[str] | None = None) -> str:
        """
        Gera a playlist do bloco usando o PlaylistEngine tradicional.
        Aceita opcionalmente uma customização de 'mood' e uma lista de 'estilos' musicais.
        Isso garante a inclusão de todos os assets (vinhetas, spots, boletins),
        tempo correto de duração (7600s/8000s) e regras estritas de rodízio de artistas/músicas.
        """
        from director.playlist_engine import playlist_engine_instance
        from director import grade_rules as GR
        import os
        try:
            if not mood:
                mood = self.obter_clima_natal()
            ok = playlist_engine_instance.gerar_playlist_bloco(hora_inicio, mood, estilos_customizados=estilos)
            if ok:
                try:
                    cfg = GR.CFG
                    nome_arquivo = f"PROG_{hora_inicio:02d}H.m3u"
                    caminho_m3u = os.path.join(cfg.get("pasta_programacao", "."), nome_arquivo)
                    pubsub_service_instance.publish("auditoria:bloco_gerado", {
                        "hora_inicio": hora_inicio,
                        "mood": mood,
                        "caminho_m3u": os.path.abspath(caminho_m3u),
                        "timestamp": now_utc().isoformat(),
                        "status": "success"
                    })
                except Exception as pe:
                    logger.error(f"Erro ao publicar evento de bloco gerado: {pe}")
                return "Sucesso na geração da playlist pelo motor."
            else:
                return "Falha ao gerar playlist via motor (retorno falso do engine)."
        except Exception as e:
            return f"Erro no motor de regras: {e}"

    def _gerar_bloco_unico(self, hora_inicio: int, mood: str | None) -> dict:
        self.log_action("PLAYLIST_GEN_START", hora=hora_inicio)
        
        # Opcionalmente, se o mood não for fornecido, pega do clima
        if not mood:
            mood = self.obter_clima_natal()

        system_prompt = (
            "Você é o Agente Programador Autônomo do Omni Core V3.\n"
            "Sua missão é gerar a programação artística do bloco das {hora_inicio:02d}H de forma otimizada.\n"
            "Siga rigorosamente estes passos:\n"
            "1. Chame 'obter_informacoes_contexto' para analisar a hora, o clima atual, o mês (sazonalidade) e as diretrizes do bloco.\n"
            "2. Analise os dados obtidos. Tome decisões criativas para adequar a programação:\n"
            "   - Por exemplo, se o clima for 'Chuvoso' mas o mês for 6 (época junina), mescle estilos do clima com ritmos tradicionais (como 'forró', 'regional', 'xote', 'baião').\n"
            "   - Selecione um mood adequado e monte uma lista personalizada de estilos musicais coerente.\n"
            "3. Chame 'gerar_playlist_via_motor' passando a hora de início, o 'mood' e a lista customizada de 'estilos' escolhida.\n"
            "O motor de regras atuará como o cinto de segurança físico garantindo a conformidade regulatória."
        ).format(hora_inicio=hora_inicio)
        task = f"Analisar o contexto operacional de clima/sazonalidade e gerar a programação personalizada para o bloco de {hora_inicio:02d}H"
        try:
            res = self.run_agent_loop(task, system_prompt, max_steps=3)
            # Se res falhou ou não chamou a ferramenta, rodamos o motor diretamente como fallback garantido
            if res.get("status") != "success":
                from director.playlist_engine import playlist_engine_instance
                from director import grade_rules as GR
                import os
                ok = playlist_engine_instance.gerar_playlist_bloco(hora_inicio, mood)
                if ok:
                    try:
                        cfg = GR.CFG
                        nome_arquivo = f"PROG_{hora_inicio:02d}H.m3u"
                        caminho_m3u = os.path.join(cfg.get("pasta_programacao", "."), nome_arquivo)
                        pubsub_service_instance.publish("auditoria:bloco_gerado", {
                            "hora_inicio": hora_inicio,
                            "mood": mood,
                            "caminho_m3u": os.path.abspath(caminho_m3u),
                            "timestamp": now_utc().isoformat(),
                            "status": "success"
                        })
                    except Exception as pe:
                        logger.error(f"Erro no PubSub no fallback: {pe}")
                    return {"status": "success", "result": "Playlist gerada com sucesso via fallback do motor de regras.", "violations": []}
                else:
                    return {"status": "failed", "violations": ["Falha ao gerar playlist via motor de regras (fallback)."]}
            return {"status": "success", "result": res.get("result"), "violations": []}
        except Exception as e:
            logger.error(f"Erro crítico no loop do agente para o bloco {hora_inicio:02d}H: {e}. Executando fallback do motor.")
            # Fallback direto em caso de exceção no loop do agente
            try:
                from director.playlist_engine import playlist_engine_instance
                from director import grade_rules as GR
                import os
                ok = playlist_engine_instance.gerar_playlist_bloco(hora_inicio, mood)
                if ok:
                    try:
                        cfg = GR.CFG
                        nome_arquivo = f"PROG_{hora_inicio:02d}H.m3u"
                        caminho_m3u = os.path.join(cfg.get("pasta_programacao", "."), nome_arquivo)
                        pubsub_service_instance.publish("auditoria:bloco_gerado", {
                            "hora_inicio": hora_inicio,
                            "mood": mood,
                            "caminho_m3u": os.path.abspath(caminho_m3u),
                            "timestamp": now_utc().isoformat(),
                            "status": "success"
                        })
                    except Exception as pe:
                        logger.error(f"Erro no PubSub no fallback de exceção: {pe}")
                    return {"status": "success", "result": "Playlist gerada com sucesso via fallback pós-erro do motor.", "violations": []}
            except Exception as fe:
                logger.error(f"Erro no fallback do motor de regras: {fe}")
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

            # ── Passo 1: Loop principal de geração (com IA + fallback de motor) ────
            for hora in range(0, 24, 2):
                res_bloco = self._gerar_bloco_unico(hora, mood)
                if res_bloco["status"] == "success":
                    sucessos += 1
                else:
                    erros += 1
                    violations.extend(res_bloco["violations"])
                metadata_blocos[f"{hora:02d}H"] = res_bloco

            # ── Passo 2: Retry automático para blocos com falha (motor direto) ─────
            blocos_com_falha = [
                hora for hora in range(0, 24, 2)
                if metadata_blocos.get(f"{hora:02d}H", {}).get("status") != "success"
            ]
            if blocos_com_falha:
                logger.warning(
                    f"[PlaylistWorker] {len(blocos_com_falha)} bloco(s) falharam. "
                    f"Iniciando retry via motor direto para: {[f'{h:02d}H' for h in blocos_com_falha]}"
                )
                for hora in blocos_com_falha:
                    try:
                        mood_retry = mood or self.obter_clima_natal()
                        ok = playlist_engine_instance.gerar_playlist_bloco(hora, mood_retry)
                        if ok:
                            logger.info(f"[PlaylistWorker] Retry bem-sucedido para o bloco {hora:02d}H via motor direto.")
                            metadata_blocos[f"{hora:02d}H"]["status"] = "success_retry"
                            erros -= 1
                            sucessos += 1
                        else:
                            logger.error(f"[PlaylistWorker] Retry do motor direto também falhou para o bloco {hora:02d}H.")
                            metadata_blocos[f"{hora:02d}H"]["retry"] = "failed"
                    except Exception as re:
                        logger.error(f"[PlaylistWorker] Exceção no retry do bloco {hora:02d}H: {re}")
                        metadata_blocos[f"{hora:02d}H"]["retry"] = f"error: {re}"

            # ── Passo 3: Relatório consolidado — mensagem única via ntfy ──────────
            try:
                from core.time_utils import now_local
                from services.notification_service import send_ntfy, send_whatsapp_alert

                icones = {
                    "success": "✅",
                    "success_retry": "🔁",
                    "partial_success": "⚠️",
                    "failed": "❌",
                }
                linhas_blocos = []
                for hora in range(0, 24, 2):
                    chave = f"{hora:02d}H"
                    status_bloco = metadata_blocos.get(chave, {}).get("status", "failed")
                    icone = icones.get(status_bloco, "❓")
                    linhas_blocos.append(f"{icone} {chave}")

                # Divide em 2 linhas de 6 blocos para caber bem no ntfy
                linha1 = "  ".join(linhas_blocos[:6])
                linha2 = "  ".join(linhas_blocos[6:])

                status_geral = "success" if erros == 0 else ("partial_success" if sucessos > 0 else "failed")
                emoji_geral = "✅" if erros == 0 else ("⚠️" if sucessos > 0 else "❌")
                data_hoje = now_local().strftime("%d/%m/%Y")

                msg_relatorio = (
                    f"📻 PROGRAMAÇÃO DIÁRIA — {data_hoje}\n"
                    f"\n"
                    f"{linha1}\n"
                    f"{linha2}\n"
                    f"\n"
                    f"{emoji_geral} {sucessos}/12 blocos gerados"
                )
                if erros > 0:
                    msg_relatorio += f"\n⚠️ {erros} blocos com falha"
                retries_ok = sum(
                    1 for h in range(0, 24, 2)
                    if metadata_blocos.get(f"{h:02d}H", {}).get("status") == "success_retry"
                )
                if retries_ok > 0:
                    msg_relatorio += f"\n🔁 {retries_ok} bloco(s) recuperados via retry"

                # Silenciado para centralizar relatos no CommunicationWorker
                # send_ntfy(msg_relatorio, title="Programação Gerada")
                # logger.info(f"[PlaylistWorker] Relatório consolidado enviado via ntfy.")
                pass
            except Exception as ne:
                logger.error(f"[PlaylistWorker] Erro ao processar relatório consolidado: {ne}")

            # ── Status final ──────────────────────────────────────────────────────
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
                msg = (
                    f"Geração automática de programação diária 24h concluída. "
                    f"{sucessos} blocos com sucesso, {erros} erros."
                )
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
