import logging
from datetime import datetime, timedelta
from typing import Any

from core.worker_base import WorkerBase, WorkerResult
from core.reward import RewardStore
from core.database import SessionLocal
from core.models import AutopilotLog
from services.guardian_service import guardian_instance
from services.notification_service import send_whatsapp_alert

logger = logging.getLogger("OmniCore.Workers.Communication")

class CommunicationWorker(WorkerBase):
    """
    Worker responsável por centralizar os relatos e comunicados da rádio,
    enviando resumos consolidados no ntfy/WhatsApp apenas 2 vezes por dia.
    """
    def __init__(self, reward_store: RewardStore | None = None, config: dict[str, Any] | None = None):
        super().__init__(name="CommunicationWorker", reward_store=reward_store, config=config)

    def run_cycle(self, **kwargs) -> WorkerResult:
        try:
            self.log_action("COMMUNICATION_SUMMARY_START")
            
            # 1. Conecta ao banco de dados SQLite para ler o AutopilotLog das últimas 12 horas
            db = SessionLocal()
            logs_recentes = []
            try:
                limite_tempo = datetime.utcnow() - timedelta(hours=12)
                logs_recentes = (
                    db.query(AutopilotLog)
                    .filter(AutopilotLog.timestamp >= limite_tempo)
                    .order_by(AutopilotLog.timestamp.asc())
                    .all()
                )
            except Exception as dbe:
                logger.error(f"Erro ao buscar logs do AutopilotLog: {dbe}")
            finally:
                db.close()

            # 2. Coleta eventos recentes em memória da rádio via guardian_instance
            eventos_recentes = []
            if hasattr(guardian_instance, "events_list"):
                eventos_recentes = list(guardian_instance.events_list)

            # 3. Consolida as informações
            playlists_geradas = []
            autocura_acoes = []
            outros_erros = []
            
            # Analisa logs do AutopilotLog
            for log in logs_recentes:
                if log.action_type == "PLAYLIST_GEN":
                    playlists_geradas.append(log.message)
                elif log.action_type in ["PROCESS_RESTART", "BUTT_RECONNECT", "SILENCE_RECOVERY"]:
                    status_prefix = "✅" if log.success else "❌"
                    autocura_acoes.append(f"{status_prefix} {log.message}")
                elif not log.success:
                    outros_erros.append(log.message)

            # Analisa eventos em memória (busca regenerações e falhas na direção musical)
            reg_seen = set()
            for evt in eventos_recentes:
                msg = evt.get("message", "")
                evt_type = evt.get("type", "")
                if evt_type == "DIRECTOR" and "regenerado" in msg.lower():
                    if msg not in reg_seen:
                        autocura_acoes.append(f"🔁 Direção Musical: {msg}")
                        reg_seen.add(msg)
                elif evt_type == "ERROR" and "DIREÇÃO MUSICAL" in msg:
                    if msg not in reg_seen:
                        outros_erros.append(f"🚨 {msg}")
                        reg_seen.add(msg)

            # 4. Constrói o texto do relatório
            data_hoje = datetime.now().strftime("%d/%m/%Y %H:%M")
            
            linhas = [
                f"📻 *RESUMO DA OPERAÇÃO DIÁRIA — {data_hoje}*",
                "\n*📊 PROGRAMAÇÃO DE PLAYLISTS*"
            ]
            
            if playlists_geradas:
                for pg in playlists_geradas:
                    linhas.append(f"• {pg}")
            else:
                linhas.append("• Nenhuma geração de grade diária de 24h registrada nas últimas 12 horas.")

            linhas.append("\n*🔄 AUTOCURA E RESILIÊNCIA*")
            if autocura_acoes:
                for ac in autocura_acoes:
                    linhas.append(f"• {ac}")
            else:
                linhas.append("• Operação 100% estável. Nenhuma falha/intervenção necessária nas últimas 12 horas.")

            if outros_erros:
                # Remove potenciais duplicatas nos outros_erros
                erros_limpos = list(dict.fromkeys(outros_erros))
                linhas.append("\n*⚠️ ALERTAS / ERROS NÃO RESOLVIDOS*")
                for err in erros_limpos:
                    linhas.append(f"• {err}")
            
            msg_completa = "\n".join(linhas)
            
            # Determina o título dinâmico e objetivo para o relatório de ntfy
            if outros_erros:
                titulo = "🚨 Status: Falhas Operacionais Pendentes"
            elif autocura_acoes:
                intervencoes = len(autocura_acoes)
                titulo = f"⚠️ Status: Estabilizado via Autocura ({intervencoes}x)"
            else:
                titulo = "✅ Status: Transmissão 100% Estável"

            # Envia as mensagens consolidadas
            send_whatsapp_alert(msg_completa, title=titulo)
            
            return WorkerResult(
                status="success",
                score=10,
                metadata={
                    "message": "Relatório consolidado enviado com sucesso.",
                    "playlists_geradas_count": len(playlists_geradas),
                    "autocura_acoes_count": len(autocura_acoes),
                    "erros_count": len(outros_erros)
                }
            )
        except Exception as e:
            logger.error(f"Erro no CommunicationWorker: {e}")
            return WorkerResult(status="error", score=-5, violations=[str(e)])
