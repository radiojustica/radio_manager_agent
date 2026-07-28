"""
NtfyListenerService
=====================
Escuta o canal `radio_tjrn` via SSE (long-poll) e detecta comandos de operação
remota. Ao receber um comando válido, dispara o worker correspondente e publica
o resultado de volta no mesmo canal.

Anti-loop
---------
Os comandos são frases fixas que NUNCA aparecem em mensagens automáticas do
sistema (relatórios, alertas, heartbeats). Isso impede que o listener reaja
às próprias notificações e crie um loop de feedback.

Interface inteligente
---------------------
O listener normaliza a mensagem do usuário (trim, lower, remoção de acentos,
colapsagem de espaços) antes de casar. Isso permite variações como:
  "gerar playlist agora", "quero playlist", "faz playlist" etc.

Comandos disponíveis (envie pelo app ntfy no canal radio_tjrn):
    gerar playlist / gerar 24h    → PlaylistWorker        (geração diária)
    ativar spider                  → SpiderWorker          (varredura do Drive)
    sincronizar acervo             → SyncWorker            (sync do banco)
    sincronizar boletins           → BulletinSync          (download de boletins)
    checar saude / status / no ar  → consulta de estado
    ajuda / comandos / help        → lista de comandos
    relatorio diario               → DailyReportWorker
"""

import logging
import threading
import time
import json
import requests
import unicodedata
import re

logger = logging.getLogger("OmniCore.NtfyListener")

# ---------------------------------------------------------------------------
# Configuração do canal
# ---------------------------------------------------------------------------

NTFY_CHANNEL = "radio_tjrn"
NTFY_SSE_URL = "https://ntfy.sh/" + NTFY_CHANNEL + "/sse"
NTFY_POST_URL = "https://ntfy.sh/" + NTFY_CHANNEL

# Tempo de espera antes de reconectar apos falha de rede
RECONNECT_DELAY = 15

# ---------------------------------------------------------------------------
# Normalização de texto para matching robusto
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    """
    Normaliza texto para matching de comandos:
    1. Lowercase
    2. Remove acentos
    3. Remove pontuação e caracteres especiais (mantém letras, dígitos e espaço)
    4. Colapsa espaços múltiplos
    5. Trim
    """
    t = text.lower().strip()
    # Remove acentos
    t = unicodedata.normalize("NFD", t)
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    # Remove pontuação e caracteres especiais, mantém letras, dígitos e espaço
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    # Colapsa espaços múltiplos
    t = re.sub(r"\s+", " ", t).strip()
    return t


# ---------------------------------------------------------------------------
# Mapa de comandos -> workers ou funções customizadas
# ---------------------------------------------------------------------------

COMMAND_MAP = {
    "gerar playlist":     ("PlaylistWorker",      {}),
    "gerar playlists":    ("PlaylistWorker",      {}),
    "playlists de hoje":  ("PlaylistWorker",      {}),
    "gerar 24h":          ("PlaylistWorker",      {}),
    "gerar grade":        ("PlaylistWorker",      {}),
    "ativar spider":      ("SpiderWorker",         {}),
    "spider":             ("SpiderWorker",         {}),
    "varrer drive":       ("SpiderWorker",         {}),
    "sincronizar acervo": ("SyncWorker",           {}),
    "sync acervo":        ("SyncWorker",           {}),
    "sincronizar boletins":("BulletinSync",        {}),
    "sync boletins":      ("BulletinSync",        {}),
    "boletins":           ("BulletinSync",        {}),
    "checar saude":       ("GuardianWorker",       {}),
    "checar health":      ("GuardianWorker",       {}),
    "status":             ("GuardianWorker",       {}),
    "no ar":              ("GuardianWorker",       {}),
    "baixar musicas":     ("DownloaderWorker",     {}),
    "baixar musica":      ("DownloaderWorker",     {}),
    "download musicas":   ("DownloaderWorker",     {}),
    "relatorio diario":   ("DailyReportWorker",    {}),
    "relatorio":          ("DailyReportWorker",    {}),
    "diario":             ("DailyReportWorker",    {}),
    "report":             ("DailyReportWorker",    {}),
}

# Comandos diretos de consulta ou ações customizadas (executados sem worker manager)
CUSTOM_COMMANDS = (
    "ver estado da transmissao",
    "estado da transmissao",
    "status do ar",
    "status",
    "no ar",
    "sincronizar boletins",
    "sync boletins",
    "boletins",
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
    "programacao diaria",
    "programação diária",
    "blocos gerados",
    "bloco(s) recuperados",
    "programacao gerada",
    # --- Proprio listener (anti-loop primario) ---
    "[cmd:",
    "[ok] ",
    "[erro] ",
    "concluido\nstatus:",
    "disparado remotamente",
    "disparando ",
    # --- Alertas do GuardianWorker / notification_service ---
    "alerta",
    "autopilot",
    "zararadio",
    "encoder butt",
    "silencio detectado",
    "silêncio detectado",
    # --- Relatorio gerencial (daily_report_worker.py) ---
    "relatorio gerencial",
    "relatório gerencial",
    "omni core",
    "omnicore",
    # --- Notificacoes genericas do sistema ---
    "notificacao ntfy enviada",
    "alerta de operacao",
)

# Mensagem de erro padrão quando o comando não é reconhecido
MSG_UNKNOWN_COMMAND = (
    "⚠️ Comando não reconhecido.\n"
    "Envie 'ajuda' para ver os comandos disponíveis."
)

MSG_HELP = (
    "📋 COMANDOS DISPONÍVEIS (Canal radio_tjrn):\n\n"
    "• 'gerar playlist' ou 'gerar 24h' — gera grade do dia\n"
    "• 'ativar spider' — varredura do Drive\n"
    "• 'sincronizar acervo' — sync do banco de músicas\n"
    "• 'sincronizar boletins' — baixa boletins do GDrive\n"
    "• 'baixar músicas' — aquisição proativa\n"
    "• 'checar saude' ou 'status' — estado da transmissão\n"
    "• 'relatório' — relatório gerencial\n"
    "• 'ajuda' — esta mensagem"
)


class NtfyListenerService:
    """
    Thread daemon que escuta o canal ntfy via SSE e executa comandos remotos.
    Usa normalização de texto para matching robusto e mapa de frases fixas
    para evitar loop com as próprias notificações.
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
            logger.warning("[NtfyListener] Já está em execução.")
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
    # Loop SSE com reconexao automática
    # ------------------------------------------------------------------

    def _listen_loop(self):
        while self._running:
            try:
                self._consume_sse()
            except Exception as e:
                if self._running:
                    logger.error(
                        "[NtfyListener] Conexão SSE encerrada (%s). Reconectando em %ds...",
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
            logger.info("[NtfyListener] Conexão SSE estabelecida. Aguardando comandos...")

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
            logger.debug("[NtfyListener] Evento SSE ignorado (não é JSON): %s", data_str[:80])
            return

        # Ignora eventos de infraestrutura do ntfy (open, keepalive)
        event_type = payload.get("event", "")
        if event_type in ("open", "keepalive"):
            return

        message = payload.get("message", "").strip()
        if not message:
            return

        # ── Anti-loop: descarta mensagens geradas pelo próprio sistema ───────
        msg_lower = message.lower()
        for pattern in SYSTEM_PATTERNS:
            if pattern.lower() in msg_lower:
                logger.debug(
                    "[NtfyListener] Mensagem do sistema ignorada (anti-loop, padrão=%r): %s",
                    pattern, message[:60],
                )
                return

        # ── Normaliza e tenta casar com comandos de worker registrados ────────
        normalized = _normalize(message)

        # Primeiro: comandos customizados de consulta
        custom_match = self._match_custom_command(normalized)
        if custom_match:
            return

        # Segundo: comandos de worker registrados
        worker_match = self._match_worker_command(normalized)
        if worker_match:
            frase_key, worker_name, kwargs_extra = worker_match
            logger.info(
                "[NtfyListener] Comando '%s' detectado (normalized: '%s') -> worker '%s'",
                frase_key, normalized, worker_name,
            )
            self._executar_worker(worker_name, kwargs_extra)
            return

        # Nenhum comando reconhecido — pode ser uma mensagem humana sem comando
        logger.debug(
            "[NtfyListener] Mensagem sem comando reconhecido ignorada: %s",
            message[:60],
        )
        self._publicar(MSG_UNKNOWN_COMMAND, title="Omni Core - Comando")

    def _match_custom_command(self, normalized: str):
        """Tenta casar com comandos customizados de consulta."""
        for cmd in CUSTOM_COMMANDS:
            normalized_cmd = _normalize(cmd)
            if normalized_cmd in normalized:
                logger.info("[NtfyListener] Comando customizado '%s' detectado (normalized)", cmd)
                self._tratar_comando_customizado(cmd)
                return True
        return False

    def _match_worker_command(self, normalized: str):
        """
        Tenta casar com um comando de worker registrado.
        Usa matching de substring após normalização para ser mais tolerante.
        """
        for frase_key, (worker_name, kwargs_extra) in COMMAND_MAP.items():
            normalized_frase = _normalize(frase_key)
            # O frase inteira deve estar contida na mensagem normalizada
            if normalized_frase and normalized_frase in normalized:
                return (frase_key, worker_name, kwargs_extra)

            # Também aceita matching parcial por palavras-chave (mínimo 3 palavras na frase)
            palavras = normalized_frase.split()
            if len(palavras) >= 3:
                # Verifica se pelo menos 2 das 3+ palavras estão presentes
                hits = sum(1 for p in palavras if p and p in normalized)
                if hits >= max(2, len(palavras) - 1):
                    return (frase_key, worker_name, kwargs_extra)

        return None

    def _tratar_comando_customizado(self, cmd: str):
        """Trata comandos que não dependem diretamente de um Worker."""
        normalized = _normalize(cmd)
        if any(w in normalized for w in ("estado", "status", "no ar")):
            self._responder_status_transmissao()
        elif any(w in normalized for w in ("ajuda", "comandos", "help")):
            self._responder_ajuda()
        elif "boletins" in normalized or "sync boletins" in normalized or "sincronizar boletins" in normalized:
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
                "📻 OMNI CORE - ESTADO DA TRANSMISSÃO\n"
                f"🎵 Tocando: {title}\n"
                f"📡 ZaraRadio: {status_zara}\n"
                f"🎙️ Encoders BUTT: {butt_ativos}/{butt_total} ativos\n"
                f"🎭 Campanha: {sazonalidade}"
            )
            self._publicar(msg, title="Status do Ar")
        except Exception as e:
            logger.error("[NtfyListener] Erro ao buscar status: %s", e)
            self._publicar(f"[ERRO] Falha ao consultar status: {e}", title="Erro Status")

    def _responder_ajuda(self):
        self._publicar(MSG_HELP, title="Comandos da Rádio")

    def _sincronizar_boletins_custom(self):
        try:
            from scripts.bulletin_sync import BulletinSync
            syncer = BulletinSync()
            res = syncer.sync()
            ok = res.get("success", False)
            upd = res.get("updated", 0)
            flag = "[OK]" if ok else "[ERRO]"
            self._publicar(
                f"{flag} Sincronização de Boletins: {upd} arquivos atualizados.",
                title="Boletins TJRN",
            )
        except Exception as e:
            self._publicar(f"[ERRO] Falha na sync de boletins: {e}", title="Boletins TJRN")

    # ------------------------------------------------------------------
    # Execução do worker
    # ------------------------------------------------------------------

    def _executar_worker(self, nome_worker, kwargs_extra):
        """Valida e dispara o worker solicitado, publicando o resultado no canal."""
        if self._worker_manager is None:
            logger.error("[NtfyListener] worker_manager não injetado.")
            return

        worker = self._worker_manager.get_worker(nome_worker)
        if not worker:
            disponiveis = ", ".join(self._worker_manager.workers.keys())
            logger.error("[NtfyListener] Worker '%s' não encontrado no registro.", nome_worker)
            self._publicar(
                "[CMD: ERRO] Worker '" + nome_worker + "' não registrado.\n"
                "Disponíveis: " + disponiveis,
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
                flag + " " + nome_worker + " concluído",
                "Status: " + str(status) + "  Score: " + str(score),
            ]
            if violations:
                linhas.append("Violações: " + "; ".join(str(v) for v in violations[:3]))

            self._publicar("\n".join(linhas), title="Omni Core - Resultado")
            logger.info("[NtfyListener] Worker '%s' executado. Status: %s", nome_worker, status)

        except Exception as e:
            logger.error("[NtfyListener] Erro ao executar '%s': %s", nome_worker, e)
            self._publicar(
                "[ERRO] Falha ao executar '" + nome_worker + "': " + str(e),
                title="Omni Core - Resultado",
            )

    # ------------------------------------------------------------------
    # Publicação no canal ntfy
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
