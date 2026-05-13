"""
Playlist Engine — Omni Core V2
================================
Orquestrador de geração de grades musicais.

Responsabilidades deste módulo:
  1. Consultar o banco de dados (SQLAlchemy) para filtrar o acervo por estilo.
  2. Delegar a montagem do bloco ao Motor de Regras (grade_rules.py).
  3. Escrever o arquivo .m3u no disco.
  4. Registrar eventos no GuardianService.

NÃO coloque lógica de negócio aqui. Toda regra de grade fica em grade_rules.py.
"""

import os
import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from core.database import SessionLocal
from core.models import Musica
from services.guardian_service import guardian_instance
from director import grade_rules as GR
from director.actor_critic import actor_critic_instance
from services import weather_service

logger = logging.getLogger("OmniCore.PlaylistEngine")


class PlaylistEngine:
    """Gera arquivos M3U de grade musical usando as regras definidas em grade_rules.py."""

    def _sync_bulletins_before_gen(self):
        """Dispara a sincronização de boletins antes de gerar grades."""
        try:
            from routers.status import bulletin_syncer
            bulletin_syncer.sync()
        except Exception as e:
            logger.error(f"[Engine] Erro ao sincronizar boletins antes da geração: {e}")

    # ------------------------------------------------------------------
    # Consulta ao banco de dados
    # ------------------------------------------------------------------

    @staticmethod
    def _buscar_acervo(db: Session, estilos: list[str]) -> list:
        """Retorna músicas válidas priorizando as menos tocadas e mais antigas (Fair Rotation)."""
        candidatas = (
            db.query(Musica)
            .filter(
                Musica.redflag == False,
                Musica.estilo.in_(estilos),
            )
            .order_by(
                Musica.vezes_tocada.asc(),        # 1. Menos executadas primeiro
                Musica.ultima_reproducao.asc()    # 2. Mais antigas primeiro
            )
            .all()
        )
        if not candidatas:
            # Fallback: qualquer música sem redflag
            logger.warning(
                f"[Engine] Nenhuma música encontrada para estilos {estilos}. "
                "Usando fallback (todos os estilos)."
            )
            candidatas = (
                db.query(Musica)
                .filter(Musica.redflag == False)
                .order_by(Musica.vezes_tocada.asc(), Musica.ultima_reproducao.asc())
                .all()
            )
        return candidatas

    @staticmethod
    def _atualizar_reproducao(db: Session, musicas_tocadas: list):
        """Marca músicas como tocadas e incrementa o contador de execuções."""
        agora = datetime.utcnow()
        for m in musicas_tocadas:
            # Incremento individual para garantir atomicidade no contador
            db.query(Musica).filter(Musica.id == m.id).update(
                {
                    Musica.ultima_reproducao: agora,
                    Musica.vezes_tocada: Musica.vezes_tocada + 1
                },
                synchronize_session=False,
            )
        db.commit()

    # ------------------------------------------------------------------
    # Escrita do M3U
    # ------------------------------------------------------------------

    @staticmethod
    def _escrever_m3u(linhas: list[str], caminho: str) -> bool:
        """Grava o M3U em disco com encoding compatível com ZaraRadio (cp1252)."""
        try:
            os.makedirs(os.path.dirname(caminho), exist_ok=True)
            with open(caminho, "w", encoding="cp1252", errors="replace") as f:
                f.write("\n".join(linhas))
            return True
        except Exception as e:
            logger.error(f"[Engine] Falha ao escrever M3U '{caminho}': {e}")
            return False

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def gerar_playlist_bloco(self, hora_inicio: int, mood: str | None = None) -> bool:
        """Gera o M3U de 2h para um dado bloco horário.

        Args:
            hora_inicio: Hora de início do bloco (0, 2, 4, ... 22).
            mood: Mood/Vibe a ser aplicado. Usa o padrão do settings.json se None.

        Returns:
            True em sucesso, False em falha.
        """
        # Se o mood não for passado, tenta pegar o clima real de Natal/RN
        if not mood:
            mood = weather_service.get_natal_weather_mood()
            logger.info(f"[Engine] Mood automático detectado (Natal/RN): {mood}")

        estilos = GR.estilos_para_mood(mood)
        cfg     = GR.CFG
        duracao = cfg.get("duracao_bloco_segundos", 7200)

        db = SessionLocal()
        try:
            acervo = self._buscar_acervo(db, estilos)
            if not acervo:
                logger.error(f"[Engine] Bloco {hora_inicio:02d}H: acervo vazio após fallback.")
                return False

            assets = GR.carregar_assets_apoio()
            linhas = GR.montar_bloco(acervo, duracao, assets, hora_inicio, mood)

            nome_arquivo = f"PROG_{hora_inicio:02d}H.m3u"
            caminho_m3u  = os.path.join(cfg["pasta_programacao"], nome_arquivo)

            ok = self._escrever_m3u(linhas, caminho_m3u)
            if ok:
                # INTEGRAÇÃO COM O DIRETOR MUSICAL
                from director.orchestrator import music_director_instance
                aprovado = music_director_instance.approve_or_redo(caminho_m3u, hora_inicio)
                
                if aprovado:
                    guardian_instance.log_event(
                        "ENGINE",
                        f"Playlist {nome_arquivo} aprovada e salva."
                    )
                return aprovado
            return False

        except Exception as e:
            logger.exception(f"[Engine] Erro ao gerar bloco {hora_inicio:02d}H: {e}")
            return False
        finally:
            db.close()

    def gerar_programacao_diaria(self, mood: str | None = None) -> bool:
        """Gera os 12 blocos de 2h (00H–22H) para as próximas 24h.

        Args:
            mood: Mood global aplicado a todos os blocos. Usa padrão se None.

        Returns:
            True se todos os blocos foram gerados com sucesso.
        """
        # Sincroniza boletins do GDrive antes de começar
        self._sync_bulletins_before_gen()
        
        mood = mood or GR.CFG.get("mood_padrao", "Ensolarado")
        logger.info(f"[Engine] Iniciando geração diária 24h — Mood: {mood}")
        sucesso = True

        for hora in range(0, 24, 2):
            ok = self.gerar_playlist_bloco(hora, mood)
            if not ok:
                logger.error(f"[Engine] Falha no bloco {hora:02d}H.")
                sucesso = False

        guardian_instance.log_event("SUCCESS", f"Programação 24h finalizada (Mood: {mood})")
        return sucesso

    def gerar_playlist_bloco_llm(self, hora_inicio: int, mood: str | None = None) -> bool:
        """Gera uma playlist de bloco usando o fluxo Actor-Critic com Ollama local."""
        cfg = GR.CFG
        nome_arquivo = f"PROG_LLM_{hora_inicio:02d}H.m3u"
        caminho_m3u = os.path.join(cfg["pasta_programacao"], nome_arquivo)

        ok = actor_critic_instance.run_cycle(hora_inicio, mood, caminho_m3u)
        if ok:
            guardian_instance.log_event(
                "ENGINE",
                f"Playlist LLM {nome_arquivo} aprovada e salva."
            )
        else:
            guardian_instance.log_event(
                "ENGINE",
                f"Playlist LLM {nome_arquivo} reprovada pelo crítico."
            )
        return ok

    def gerar_programacao_diaria_llm(self, mood: str | None = None) -> bool:
        """Gera a programação de 24h usando o fluxo Actor-Critic."""
        mood = mood or GR.CFG.get("mood_padrao", "Ensolarado")
        logger.info(f"[Engine] Iniciando geração diária LLM — Mood: {mood}")
        sucesso = True

        for hora in range(0, 24, 2):
            ok = self.gerar_playlist_bloco_llm(hora, mood)
            if not ok:
                logger.error(f"[Engine] Falha no bloco LLM {hora:02d}H.")
                sucesso = False

        guardian_instance.log_event("SUCCESS", f"Programação 24h LLM finalizada (Mood: {mood})")
        return sucesso

    def gerar_bloco_extra(self, mood: str | None = None) -> bool:
        """Gera uma playlist cobrindo o tempo restante no bloco atual (Horário Quebrado).

        Args:
            mood: Mood a aplicar. Usa padrão se None.

        Returns:
            True em sucesso, False em falha.
        """
        mood = mood or GR.CFG.get("mood_padrao", "Ensolarado")
        estilos = GR.estilos_para_mood(mood)
        cfg     = GR.CFG

        segundos = GR.segundos_restantes_no_bloco()
        logger.info(f"[Engine] Gerando Bloco Extra: {segundos}s restantes, mood={mood}")

        db = SessionLocal()
        try:
            acervo = self._buscar_acervo(db, estilos)
            if not acervo:
                logger.error("[Engine] Bloco Extra: acervo vazio.")
                return False

            assets = GR.carregar_assets_apoio()
            linhas = GR.montar_bloco(acervo, segundos, assets)

            agora = datetime.now()
            nome_arquivo = f"PROG_EXTRA_{agora.strftime('%H%M')}.m3u"
            caminho_m3u  = os.path.join(cfg["pasta_programacao"], nome_arquivo)

            ok = self._escrever_m3u(linhas, caminho_m3u)
            if ok:
                guardian_instance.log_event(
                    "SUCCESS",
                    f"Bloco Extra '{nome_arquivo}' criado ({segundos}s, mood={mood})"
                )
            return ok

        except Exception as e:
            logger.exception(f"[Engine] Erro ao gerar Bloco Extra: {e}")
            return False
        finally:
            db.close()

    def auto_gerar_proximos_blocos(self) -> None:
        """Job automático: garante que o bloco atual e o próximo existam no disco.

        Regenera se o arquivo não existir ou tiver mais de 20h de idade.
        Chamado a cada hora pelo APScheduler.
        """
        # Sincroniza boletins do GDrive
        self._sync_bulletins_before_gen()
        
        now = datetime.now()
        bloco_atual  = (now.hour // 2) * 2
        bloco_proximo = (bloco_atual + 2) % 24
        pasta = GR.CFG["pasta_programacao"]

        for hora in [bloco_atual, bloco_proximo]:
            caminho = os.path.join(pasta, f"PROG_{hora:02d}H.m3u")
            try:
                precisa = (
                    not os.path.exists(caminho)
                    or (now - datetime.fromtimestamp(os.path.getmtime(caminho))) > timedelta(hours=20)
                )
                if precisa:
                    logger.info(f"[Engine.auto] Gerando bloco {hora:02d}H")
                    self.gerar_playlist_bloco(hora)
            except Exception as e:
                logger.error(f"[Engine.auto] Erro no bloco {hora:02d}H: {e}")


# Instância global (usada pelo APScheduler e pelos routers)
playlist_engine_instance = PlaylistEngine()


