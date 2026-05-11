from email.mime.base import MIMEBase
from email import encoders
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import logging
from datetime import datetime

# Placeholder values that indicate credentials were never configured
_PLACEHOLDER_VALUES = {"YOUR_GMAIL@gmail.com", "YOUR_APP_PASSWORD", "", None}


class EmailReporter:
    def __init__(self, config: dict):
        self.config = config
        self.logger = logging.getLogger("RadioManagerAgent.EmailReporter")
        self.smtp_server   = config.get("smtp_server", "smtp.gmail.com")
        self.smtp_port     = config.get("smtp_port", 587)
        self.sender_email  = config.get("sender_email", "")
        self.sender_password = config.get("sender_password", "")
        # target_email comes from config — not hardcoded
        self.target_email  = config.get("target_email", "")

    @property
    def is_configured(self) -> bool:
        """Returns True only if SMTP credentials are real (non-placeholder) values."""
        return (
            self.sender_email not in _PLACEHOLDER_VALUES
            and self.sender_password not in _PLACEHOLDER_VALUES
            and bool(self.target_email)
        )

    def send_daily_report(self, summary_data: dict, attachment_path: str = None) -> bool:
        """Sends the daily operation report via email with optional attachment."""
        if not self.is_configured:
            self.logger.warning(
                "Email report skipped: SMTP credentials are missing or still set to placeholders. "
                "Please update config/settings.json."
            )
            return False

        msg = MIMEMultipart()
        msg['From']    = self.sender_email
        msg['To']      = self.target_email
        msg['Subject'] = f"RELATÓRIO DE OPERAÇÃO — {datetime.now().strftime('%d/%m/%Y')}"

        body = self.generate_html_body(summary_data)
        msg.attach(MIMEText(body, 'html', 'utf-8'))

        # Add attachment if provided
        if attachment_path and os.path.exists(attachment_path):
            try:
                with open(attachment_path, "rb") as attachment:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={os.path.basename(attachment_path)}",
                    )
                    msg.attach(part)
            except Exception as e:
                self.logger.error(f"Failed to attach file {attachment_path}: {e}")

        try:
            # Use context manager to guarantee the connection is always closed
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            self.logger.info(f"Report sent successfully to {self.target_email}")
            return True
        except smtplib.SMTPAuthenticationError:
            self.logger.error(
                "Email: Authentication failed. Check sender_email and sender_password in settings.json."
            )
            return False
        except smtplib.SMTPException as e:
            self.logger.error(f"Email: SMTP error — {e}")
            return False
        except Exception as e:
            self.logger.error(f"Email: Unexpected error — {e}")
            return False

    def generate_html_body(self, data: dict) -> str:
        """Generates a professional HTML report."""
        # Color mapping for event types
        EVENT_COLORS = {
            "INFO":         "#A6E3A1",  # green
            "RESTART":      "#F9E2AF",  # yellow
            "ERROR":        "#F38BA8",  # red
            "WARNING":      "#F9E2AF",  # yellow
            "LIVE_START":   "#89B4FA",  # blue
            "LIVE_END":     "#CBA6F7",  # purple
            "TASK_DELETED": "#FAB387",  # orange
        }
        DEFAULT_COLOR = "#CDD6F4"

        rows = ""
        for event in data.get("events", []):
            color = EVENT_COLORS.get(event.get('type', ''), DEFAULT_COLOR)
            rows += (
                f"<tr>"
                f"<td style='padding:8px; border-bottom:1px solid #313244; color:#CDD6F4;'>{event['time']}</td>"
                f"<td style='padding:8px; border-bottom:1px solid #313244; color:{color};'><b>{event['type']}</b></td>"
                f"<td style='padding:8px; border-bottom:1px solid #313244; color:#BAC2DE;'>{event['message']}</td>"
                f"</tr>"
            )

        if not rows:
            rows = (
                "<tr><td colspan='3' style='padding:12px; color:#585B70; text-align:center;'>"
                "Nenhum evento registrado nas últimas 24 horas.</td></tr>"
            )

        html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"></head>
<body style="background-color:#1E1E2E; color:#CDD6F4; font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif; padding:20px;">
    <h2 style="color:#89B4FA;">🛡️ RADIO GUARDIAN — RELATÓRIO DE OPERAÇÃO</h2>
    <p>Resumo detalhado das atividades das últimas 24 horas.</p>

    <div style="background-color:#181825; padding:15px; border-radius:8px; border-left:5px solid #89B4FA;">
        <h3 style="margin-top:0; color:#CDD6F4;">Estatísticas Gerais</h3>
        <ul>
            <li><b>ZaraRadio:</b> {data.get('zara_status', 'N/A')}</li>
            <li><b>Instâncias BUTT:</b> {data.get('butt_count', 0)} ativas</li>
            <li><b>Reinicializações:</b> {data.get('restarts', 0)}</li>
        </ul>
    </div>

    <h3 style="color:#89B4FA; margin-top:25px;">Linha do Tempo de Atividades</h3>
    <table style="width:100%; border-collapse:collapse;">
        <thead style="background-color:#313244;">
            <tr>
                <th style="padding:10px; text-align:left; color:#CDD6F4;">Hora</th>
                <th style="padding:10px; text-align:left; color:#CDD6F4;">Tipo</th>
                <th style="padding:10px; text-align:left; color:#CDD6F4;">Descrição</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>

    <p style="font-size:11px; color:#585B70; margin-top:30px;">
        Relatório gerado automaticamente por Antigravity Radio Manager Agent v2.0.<br>
        Desenvolvido por @o_thiagomacedo
    </p>
</body>
</html>"""
        return html


