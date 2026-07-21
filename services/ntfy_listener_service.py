"""
NtfyListenerService
===================
Escuta o canal `radio_tjrn` via SSE (long-poll) e detecta comandos de operacao
remota. Ao receber um comando valido, dispara o worker correspondente e publica
o resultado de volta no mesmo canal.

Anti-loop
---------
Os comandos sao frases fixas que NUNCA aparecem em mensagens automaticas do
sistema (relatorios, alertas, heartbeats). Isso impede que o listener reaja
as suas proprias notificacoes e crie um loop de feedback.

Comandos disponiveis (envie pelo app ntfy no canal radio_tjrn):
    gerar playlist      -> PlaylistWorker  (geracao diaria 24h)
    ativar spider       -> SpiderWorker    (varredura do Drive)
    sincronizar acervo  -> SyncWorker      (sync do banco de musicas)
    checar saude        -> GuardianWorker  (ciclo de watchdog)
    baixar musicas      -> DownloaderWorker (aquisicao proativa)
    relatorio diario    -> DailyReportWorker (relatorio gerencial)
"""
import logging
import threading
import time
import json
import requests

logger = logging.getLogger("OmniCore.NtfyListener")

# ---------------------------------------------------------------------------
# Configuracao do canal
# ---------------------------------------------------------------------------

NTFY_CHANNEL = "radio_tjrn"
NTFY_SSE_URL = "https://ntfy.sh/" + NTFY_CHANNEL + "/sse"
NTFY_POST_URL = "https://ntfy.sh/" + NTFY_CHANNEL

# Tempo de espera antes de reconectar apos falha de rede
RECONNECT_DELAY = 15

# ---------------------------------------------------------------------------
# Mapa de comandos -> workers ou funções customizadas
# ---------------------------------------------------------------------------

COMMAND_MAP = {
    "gerar playlist":     ("PlaylistWorker",      {}),
    "gerar playlists":    ("PlaylistWorker",      {}),
    "playlists de hoje":  ("PlaylistWorker",      {}),
    "gerar 24h":          ("PlaylistWorker",      {}),
    "ativar spider":      ("SpiderWorker",         {}),
    "sincronizar acervo": ("SyncWorker",           {}),
    "checar saude":       ("GuardianWorker",       {}),
    "baixar musicas":     ("DownloaderWorker",     {}),
    "relatorio diario":   ("DailyReportWorker",    {}),
}

# Comandos diretos de consulta ou ações customizadas (executados sem worker manager)
CUSTOM_COMMANDS = (
    "ver estado da transmissão",
    "ver estado da transmissao",
    "estado da transmissao",
    "estado da transmissão",
    "status",
    "no ar",
    "sincronizar boletins",
    "ajuda",
    "comandos",
    "help",
)


# Padroes anti-loop: substrings que identificam mensagens automaticas do sistema.
# O listener descarta qualquer mensagem que contenha uma dessas strings,
# impedindo que ele reaja as proprias notificacoes e crie um loop de feedback.
# Regra: nunca use nenhuma dessas strings em comandos manuais enviados pelo app.
SYSTEM_PATTERNS = (
    # --- Relatorio de playlist (playlist_worker.py) ---
    "PROGRAMACAO DIARIA",   # corpo do relatorio diario de playlist
    "PROGRAMAÇÃO DIÁRIA",
    "blocos gerados",
    "bloco(s) recuperados",
    "Programacao Gerada",
    # --- Proprio listener (anti-loop primario) ---
    "[CMD:",
    "[OK] ",
    "[ERRO] ",
    "concluido\nStatus:",
    "disparado remotamente",
    "Disparando ",
    # --- Alertas do GuardianWorker / notification_service ---
    "ALERTA",
    "Autopilot",
    "ZaraRadio",
    "encoder BUTT",
    "Silencio detectado",
    "Silêncio detectado",
    # --- Relatorio gerencial (daily_report_worker.py) ---
    "RELATORIO GERENCIAL",
    "RELATÓRIO GERENCIAL",
    "OMNI CORE",
    "Omni Core",
    # --- Notificacoes genericas do sistema ---
    "Notificacao ntfy enviada",
    "Alerta de Operacao",
    "Alerta de Operação",
)


class NtfyListenerService:
    """
    Thread daemon que escuta o canal ntfy via SSE e executa comandos remotos.
    Usa mapa de frases fixas para evitar loop com as proprias notificacoes.
    """

    def __init__(self):
        self._running = False
        self._thread = None
        self._worker_manager = None

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------

    def start(self, worker_manager):
        """Inicia o listener em uma thread daemon."""
        if self._running:
            logger.warning("[NtfyListener] Ja esta em execucao.")
            return

        self._worker_manager = worker_manager
        self._running = True

        self._thread = threading.Thread(
            target=self._listen_loop,
            name="NtfyListenerThread",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "[NtfyListener] Listener iniciado no canal ntfy.sh/%s. "
            "Comandos: %s",
            NTFY_CHANNEL,
            ", ".join(COMMAND_MAP.keys()),
        )

    def stop(self):
        """Para o listener."""
        self._running = False
        logger.info("[NtfyListener] Listener encerrado.")

    # ------------------------------------------------------------------
    # Loop SSE com reconexao automatica
    # ------------------------------------------------------------------

    def _listen_loop(self):
        while self._running:
            try:
                self._consume_sse()
            except Exception as e:
                if self._running:
                    logger.error(
                        "[NtfyListener] Conexao SSE encerrada (%s). Reconectando em %ds...",
                        e, RECONNECT_DELAY,
                    )
                    time.sleep(RECONNECT_DELAY)

    def _consume_sse(self):
        logger.info("[NtfyListener] Conectando ao SSE: %s", NTFY_SSE_URL)
        with requests.get(
            NTFY_SSE_URL,
            stream=True,
            timeout=(10, None),
            headers={"Accept": "text/event-stream"},
        ) as resp:
            resp.raise_for_status()
            logger.info("[NtfyListener] Conexao SSE estabelecida. Aguardando comandos...")

            buffer = ""
            for chunk in resp.iter_content(chunk_size=None, decode_unicode=True):
                if not self._running:
                    break
                buffer += chunk
                while "\n\n" in buffer:
                    evento, buffer = buffer.split("\n\n", 1)
                    self._processar_evento_sse(evento)

    # ------------------------------------------------------------------
    # Processamento de eventos SSE
    # ------------------------------------------------------------------

    def _processar_evento_sse(self, evento_raw):
        linhas = evento_raw.strip().splitlines()
        data_str = None
        for linha in linhas:
            if linha.startswith("data:"):
                data_str = linha[len("data:"):].strip()
                break

        if not data_str:
            return

        try:
            payload = json.loads(data_str)
        except (json.JSONDecodeError, ValueError):
            logger.debug("[NtfyListener] Evento SSE ignorado (nao e JSON): %s", data_str[:80])
            return

        # Ignora eventos de infraestrutura do ntfy (open, keepalive)
        event_type = payload.get("event", "")
        if event_type in ("open", "keepalive"):
            return

        message = payload.get("message", "").strip()
        if not message:
            return

        # ── Anti-loop: descarta mensagens geradas pelo proprio sistema ───────
        # Verifica se qualquer padrao conhecido do sistema esta presente na mensagem
        msg_lower = message.lower()
        for pattern in SYSTEM_PATTERNS:
            if pattern.lower() in msg_lower:
                logger.debug(
                    "[NtfyListener] Mensagem do sistema ignorada (anti-loop, padrao=%r): %s",
                    pattern, message[:60],
                )
                return

        # ── Tenta casar com comandos customizados de consulta ────────────────
        for cmd in CUSTOM_COMMANDS:
            if cmd in msg_lower:
                logger.info("[NtfyListener] Comando customizado '%s' detectado", cmd)
                self._tratar_comando_customizado(cmd)
                return

        # ── Tenta casar com um comando de worker registrado ─────────────────
        comando_encontrado = None
        for frase, (worker_name, kwargs_extra) in COMMAND_MAP.items():
            if frase in msg_lower:
                comando_encontrado = (frase, worker_name, kwargs_extra)
                break

        if comando_encontrado is None:
            # Nao e um comando — apenas uma mensagem humana no canal, ignora silenciosamente
            logger.debug("[NtfyListener] Mensagem sem comando reconhecido ignorada: %s", message[:60])
            return

        frase, worker_name, kwargs_extra = comando_encontrado
        logger.info(
            "[NtfyListener] Comando '%s' detectado -> worker '%s'",
            frase, worker_name,
        )
        self._executar_worker(worker_name, kwargs_extra)

    def _tratar_comando_customizado(self, cmd: str):
        """Trata comandos que não dependem diretamente de um Worker."""
        if any(w in cmd for w in ("estado", "status", "no ar")):
            self._responder_status_transmissao()
        elif any(w in cmd for w in ("ajuda", "comandos", "help")):
            self._responder_ajuda()
        elif "boletins" in cmd:
            self._sincronizar_boletins_custom()

    def _responder_status_transmissao(self):
        try:
            from routers.status import get_now_playing
            from core.database import SessionLocal
            db = SessionLocal()
            try:
                data = get_now_playing(db)
            finally:
                db.close()

            title = data.get("title", "Desconhecido")
            status_zara = data.get("status", "desconhecido").upper()
            butt_ativos = data.get("butt_ativos", 0)
            butt_total = data.get("butt_count", 0)
            sazonalidade = data.get("sazonalidade", {}).get("nome", "Convencional")

            msg = (
                f"📻 OMNI CORE - ESTADO DA TRANSMISSÃO\n"
                f"🎵 Tocando: {title}\n"
                f"📡 ZaraRadio: {status_zara}\n"
                f"🎙️ Encoders BUTT: {butt_ativos}/{butt_total} ativos\n"
                f"🎭 Campanha: {sazonalidade}"
            )
            self._publicar(msg, title="Status do Ar")
        except Exception as e:
            logger.error(f"[NtfyListener] Erro ao buscar status: {e}")
            self._publicar(f"[ERRO] Falha ao consultar status: {e}", title="Erro Status")

    def _responder_ajuda(self):
        msg = (
            "📋 COMANDOS DISPONÍVEIS (Canal radio_tjrn):\n\n"
            "• 'ver estado da transmissão' ou 'status'\n"
            "• 'gerar playlist' ou 'playlists de hoje'\n"
            "• 'sincronizar acervo'\n"
            "• 'sincronizar boletins'\n"
            "• 'baixar musicas'\n"
            "• 'checar saude'\n"
            "• 'relatorio diario'\n"
            "• 'ajuda'"
        )
        self._publicar(msg, title="Comandos da Rádio")

    def _sincronizar_boletins_custom(self):
        try:
            from scripts.bulletin_sync import BulletinSync
            syncer = BulletinSync()
            res = syncer.sync()
            ok = res.get("success", False)
            upd = res.get("updated", 0)
            flag = "[OK]" if ok else "[ERRO]"
            self._publicar(f"{flag} Sincronização de Boletins: {upd} arquivos atualizados.", title="Boletins TJRN")
        except Exception as e:
            self._publicar(f"[ERRO] Falha na sync de boletins: {e}", title="Boletins TJRN")


    # ------------------------------------------------------------------
    # Execucao do worker
    # ------------------------------------------------------------------

    def _executar_worker(self, nome_worker, kwargs_extra):
        """Valida e dispara o worker solicitado, publicando o resultado no canal."""
        if self._worker_manager is None:
            logger.error("[NtfyListener] worker_manager nao injetado.")
            return

        worker = self._worker_manager.get_worker(nome_worker)
        if not worker:
            disponiveis = ", ".join(self._worker_manager.workers.keys())
            logger.error("[NtfyListener] Worker '%s' nao encontrado no registro.", nome_worker)
            self._publicar(
                "[CMD: ERRO] Worker '" + nome_worker + "' nao registrado.\n"
                "Disponiveis: " + disponiveis,
                title="Omni Core - Comando",
            )
            return

        self._publicar(
            "[CMD: OK] Disparando '" + nome_worker + "' remotamente...",
            title="Omni Core - Comando",
        )

        try:
            result = self._worker_manager.run_cycle(nome_worker, **kwargs_extra)
            status = result.get("result", {}).get("status", "desconhecido")
            score = result.get("result", {}).get("score", 0)
            violations = result.get("result", {}).get("violations", [])

            flag = "[OK]" if status in ("success", "partial_success") else "[ERRO]"
            linhas = [
                flag + " " + nome_worker + " concluido",
                "Status: " + str(status) + "  Score: " + str(score),
            ]
            if violations:
                linhas.append("Violacoes: " + "; ".join(str(v) for v in violations[:3]))

            self._publicar("\n".join(linhas), title="Omni Core - Resultado")
            logger.info("[NtfyListener] Worker '%s' executado. Status: %s", nome_worker, status)

        except Exception as e:
            logger.error("[NtfyListener] Erro ao executar '%s': %s", nome_worker, e)
            self._publicar(
                "[ERRO] Falha ao executar '" + nome_worker + "': " + str(e),
                title="Omni Core - Resultado",
            )

    # ------------------------------------------------------------------
    # Publicacao no canal ntfy
    # ------------------------------------------------------------------

    def _publicar(self, message, title="Omni Core"):
        """Publica uma mensagem no canal ntfy."""
        try:
            requests.post(
                NTFY_POST_URL,
                data=message.encode("utf-8"),
                headers={
                    "Title": title.encode("utf-8"),
                    "Tags": "robot",
                },
                timeout=10,
            )
        except Exception as e:
            logger.error("[NtfyListener] Erro ao publicar no ntfy: %s", e)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
ntfy_listener_service = NtfyListenerService()
